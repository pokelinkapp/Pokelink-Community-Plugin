import json
import os
import re

import pokelink.core_plugin as core_plugin
import pokelink.directories as directories
import pokelink.translations as translations
from pokelink import game_strings
from pokelink.json_output import write_file

import pokemon_unknown._abilities as _abilities
import pokemon_unknown._items as _items
import pokemon_unknown._moves as _moves
from pokemon_unknown._util import strip_comments

_PREFIX = "PokemonUnknown.Species."
_entries: list = []
_species_lookup: dict = {}
_national_id_lookup: dict = {}
_species_to_dex_table: dict = {}

# Map species constant (without SPECIES_ prefix) -> national dex ID for manual overrides
_NATIONAL_ID_OVERRIDES: dict = {}

_GROWTH_RATE = {
    "GROWTH_MEDIUM_FAST": 0,
    "GROWTH_ERRATIC": 1,
    "GROWTH_FLUCTUATING": 2,
    "GROWTH_MEDIUM_SLOW": 3,
    "GROWTH_FAST": 4,
    "GROWTH_SLOW": 5,
}

# Maps species constant suffixes that don't clean_up to their national dex form key.
_SUFFIX_TO_FORM_KEY: dict = {
    # Regional variant shorthands
    "A": "alola",
    "G": "galar",
    "H": "hisui",
    "P": "paldea",
    # Type forms (Arceus / Silvally) — only FIGHT differs from the type name
    "FIGHT": "fighting",
    # Species-specific name mismatches
    "EXCLAMATION": "!",
    "QUESTION": "?",
    "NOICE": "noice_face",
    "POKEBALL": "poke_ball",
    "PHAROAH": "pharaoh",       # typo in game constant
    "SUN": "sunshine",           # Cherrim
    "ASHGRENINJA": "ash",        # no common prefix with GRENINJA
    "SHOCK": "electric",         # Genesect
    "BURN": "fire",              # Genesect
    "CHILL": "ice",              # Genesect
    "DOUSE": "water",            # Genesect
    "10": "10%",                 # Zygarde 10%
    "DUSK_MANE": "dusk",         # Necrozma
    "DAWN_WINGS": "dawn",        # Necrozma
    "ICE_RIDER": "ice",          # Calyrex
    "SHADOW_RIDER": "shadow",    # Calyrex
    # Pikachu cap variants — explicit so fallback warning is suppressed
    "CAP_ORIGINAL": "original",
    "CAP_HOENN": "hoenn",
    "CAP_SINNOH": "sinnoh",
    "CAP_UNOVA": "unova",
    "CAP_KALOS": "kalos",
    "CAP_ALOLA": "alola",
    "CAP_PARTNER": "partner",
}

# Per-national-dex-ID overrides for ambiguous single-letter or species-specific suffixes.
# Checked before the global _SUFFIX_TO_FORM_KEY, so they take precedence.
_NATIONAL_ID_FORM_KEY_OVERRIDES: dict = {
    741: {"Y": "pom_pom", "P": "pau", "S": "sensu"},           # Oricorio
    745: {"N": "midnight"},                                      # Lycanroc (N = Night)
    746: {"S": "school"},                                        # Wishiwashi
    710: {"S": "small", "M": "medium", "L": "large", "XL": "super"},  # Pumpkaboo
    711: {"S": "small", "M": "medium", "L": "large", "XL": "super"},  # Gourgeist
    801: {"P": "original"},                                      # Magearna
    550: {"B": "blue", "H": "white"},                              # Basculin (base=red, .1=blue, .2=white/hisui)
    555: {"G_ZEN": "galar_zen"},                                   # Darmanitan Galarian Zen
    892: {"RAPID": "rapid_strike"},                              # Urshifu
    774: {                                                       # Minior core forms
        "RED": "c_red", "BLUE": "c_blue", "ORANGE": "c_orange",
        "YELLOW": "c_yellow", "GREEN": "c_green", "INDIGO": "c_indigo",
        "VIOLET": "c_violet",
    },
}

# Cache of national dex form maps: national_id -> {form_key: form_index}
_national_form_maps: dict = {}


def _get_national_form_map(national_id: int) -> dict:
    """Read all form entries for a national dex ID and return {form_key: n}."""
    if national_id in _national_form_maps:
        return _national_form_maps[national_id]
    form_map = {}
    n = 1
    while True:
        data = core_plugin.read_file(f"/pokemon/national/{national_id}.{n}.entry")
        if data is None:
            break
        try:
            entry = json.loads(data)
            form_name = entry.get("formName", "")
            # Extract suffix after last dot: "pokemon.form.hisui" -> "hisui"
            key = form_name.rsplit(".", 1)[-1] if "." in form_name else form_name
            if key:
                form_map[key] = n
        except Exception:
            pass
        n += 1
    _national_form_maps[national_id] = form_map
    return form_map


def _get_form_suffix(species_name: str, base_const: str) -> str:
    """Derive the form suffix from a species constant given its base species constant.
    Uses common word-boundary prefix matching so it works even when the base has a
    longer name than the form (e.g. ALCREMIE_VANILLA_CREAM base vs ALCREMIE_BERRY)."""
    if species_name.startswith(base_const + "_"):
        return species_name[len(base_const) + 1:]
    # Walk both strings; track the position after the last matching underscore
    last_boundary = 0
    for i in range(min(len(species_name), len(base_const))):
        if species_name[i] != base_const[i]:
            break
        if species_name[i] == "_":
            last_boundary = i + 1
    if last_boundary > 0:
        return species_name[last_boundary:]
    # Handle no-underscore concatenation (e.g. DARMANITANZEN over DARMANITAN)
    if species_name.startswith(base_const) and len(species_name) > len(base_const):
        return species_name[len(base_const):]
    return species_name


def _find_form_index(suffix: str, form_map: dict, national_id: int) -> tuple[int, str] | tuple[None, None]:
    """Try to match a species constant suffix to a national dex form index.
    Returns (form_index, match_strategy) or (None, None) if no match found."""
    # 0. Per-national-ID override (handles ambiguous single-letter suffixes per species)
    key = _NATIONAL_ID_FORM_KEY_OVERRIDES.get(national_id, {}).get(suffix)
    if key and key in form_map:
        return form_map[key], "per_species"
    # 1. Global explicit override
    key = _SUFFIX_TO_FORM_KEY.get(suffix)
    if key and key in form_map:
        return form_map[key], "explicit"
    # 2. Direct lowercase (handles rock_star, mega_x, phd, b/c/d for Unown, etc.)
    key = suffix.lower()
    if key in form_map:
        return form_map[key], "direct"
    # 3. Last word only (handles any remaining CAP_* style suffixes)
    key = suffix.split("_")[-1].lower()
    if key in form_map:
        return form_map[key], f"fallback(last_word='{key}')"
    return None, None


def _parse_species_to_dex_table() -> dict:
    path = os.path.join(directories.get_external_dir("pokemon-unknown"),
                        "dpe", "src", "Species_To_Pokdex_Table.c")
    table = {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.split("//")[0].strip()
            m = re.match(r'\[SPECIES_(\w+)\s*-\s*1\]\s*=\s*(NATIONAL_DEX_\w+)', line)
            if not m:
                continue
            species_name = m.group(1)
            dex_const = m.group(2)
            if dex_const == "NATIONAL_DEX_NONE":
                table[species_name] = 0
            else:
                dex_name = dex_const.removeprefix("NATIONAL_DEX_")
                clean = _species_lookup.get(dex_name.lower().replace("_", ""))
                table[species_name] = _national_id_lookup.get(clean, 0) if clean else 0
    return table


def _find_national_id(constant: str) -> int | None:
    if constant in _NATIONAL_ID_OVERRIDES:
        return _NATIONAL_ID_OVERRIDES[constant]
    if constant in _species_to_dex_table:
        return _species_to_dex_table[constant] or None
    # Fallback for species absent from the table
    clean = _species_lookup.get(constant.lower().replace("_", ""))
    return _national_id_lookup.get(clean) if clean else None


def _species_name(constant: str) -> str:
    key = constant.lower().replace("_", "")
    if key in _species_lookup:
        return "pokemon.species." + _species_lookup[key]
    display = " ".join(p[0].upper() + p[1:].lower() for p in constant.split("_"))
    xkey = _PREFIX + game_strings.clean_up(display)
    translations.add_translation(xkey, display)
    return xkey


def _gender_ratio(value_str: str) -> int:
    m = re.match(r'PERCENT_FEMALE\(([0-9.]+)\)', value_str)
    if m:
        return min(254, int(float(m.group(1)) * 255 / 100))
    if "MON_FEMALE" in value_str:
        return 254
    if "MON_GENDERLESS" in value_str:
        return 255
    try:
        return int(value_str)
    except ValueError:
        return 255


def _safe_int(s: str, constants: dict) -> int:
    s = s.strip()
    try:
        return int(s)
    except ValueError:
        return constants.get(s, 0)


def _parse_species_ids() -> dict:
    ids = {}
    path = os.path.join(directories.get_external_dir("pokemon-unknown"),
                        "cfru", "include", "constants", "species.h")
    with open(path, "r") as f:
        for line in f:
            line = line.split("//")[0].strip()
            if not line.startswith("#define SPECIES_"):
                continue
            parts = line.split()
            if len(parts) < 3:
                continue
            name = parts[1].removeprefix("SPECIES_")
            try:
                ids[name] = int(parts[2], 16)
            except ValueError:
                pass
    return ids


def _parse_base_stats() -> tuple[dict, dict]:
    path = os.path.join(directories.get_external_dir("pokemon-unknown"),
                        "dpe", "src", "Base_Stats.c")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = strip_comments(f.read())

    constants = {}
    for cm in re.finditer(r'#define\s+(\w+)\s+(\d+)', content):
        constants[cm.group(1)] = int(cm.group(2))

    stats = {}
    for m in re.finditer(r'\[SPECIES_([^\]]+)\]\s*=\s*\{([^{}]*)\}', content, re.DOTALL):
        fields = {}
        for fm in re.finditer(r'\.(\w+)\s*=\s*([^,\n]+)', m.group(2)):
            fields[fm.group(1)] = fm.group(2).strip()
        if fields:
            stats[m.group(1)] = fields

    return stats, constants


def _parse_evolutions() -> dict:
    path = os.path.join(directories.get_external_dir("pokemon-unknown"),
                        "dpe", "src", "Evolution Table.c")
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = strip_comments(f.read())

    evos = {}
    parts = re.split(r'\[SPECIES_([^\]]+)\]\s*=', content)
    for i in range(1, len(parts) - 1, 2):
        species = parts[i]
        body = parts[i + 1]
        evo_list = []
        for em in re.finditer(r'\{(EVO_[^{}]+)\}', body):
            fields = [f.strip() for f in em.group(1).split(',')]
            if len(fields) >= 3:
                evo_list.append(fields)
        if evo_list:
            evos[species] = evo_list
    return evos


def _make_evolution(fields: list, species_ids: dict) -> dict | None:
    evo_type = fields[0]
    param = fields[1]
    target = fields[2].removeprefix("SPECIES_")

    # Not possible in this ROM / unsupported by the app — skip entirely.
    # Trade and map evolutions always have an EVO_ITEM alternative in this ROM.
    if evo_type in ("EVO_MEGA", "EVO_RAINY_FOGGY_OW", "EVO_TRADE", "EVO_TRADE_ITEM", "EVO_MAP"):
        return None
    target_id = species_ids.get(target, 0)
    if not target_id:
        return None

    conditions = {}

    try:
        level = int(param)
    except ValueError:
        level = 0

    if evo_type == "EVO_LEVEL":
        conditions["pokemon.evolve.level"] = {"number": level}
    elif evo_type == "EVO_ITEM":
        conditions["pokemon.evolve.useItem"] = {"string": _items.get_item_by_constant(param.removeprefix("ITEM_"))}
    elif evo_type == "EVO_FRIENDSHIP":
        conditions["pokemon.evolve.friendship"] = {"string": "friendship.high"}
    elif evo_type == "EVO_FRIENDSHIP_DAY":
        conditions["pokemon.evolve.friendship"] = {"string": "friendship.high"}
        conditions["pokemon.evolve.time"] = {"string": "timeOfDay.day"}
    elif evo_type == "EVO_FRIENDSHIP_NIGHT":
        conditions["pokemon.evolve.friendship"] = {"string": "friendship.high"}
        conditions["pokemon.evolve.time"] = {"string": "timeOfDay.night"}
    elif evo_type == "EVO_MOVE":
        conditions["pokemon.evolve.knowMove"] = {"string": _moves.get_move_by_constant(param.removeprefix("MOVE_"))}
    elif evo_type == "EVO_LEVEL_DAY":
        conditions["pokemon.evolve.level"] = {"number": level}
        conditions["pokemon.evolve.time"] = {"string": "timeOfDay.day"}
    elif evo_type == "EVO_LEVEL_NIGHT":
        conditions["pokemon.evolve.level"] = {"number": level}
        conditions["pokemon.evolve.time"] = {"string": "timeOfDay.night"}
    elif evo_type == "EVO_HOLD_ITEM_DAY":
        conditions["pokemon.evolve.hasItem"] = {"string": _items.get_item_by_constant(param.removeprefix("ITEM_"))}
        conditions["pokemon.evolve.time"] = {"string": "timeOfDay.day"}
    elif evo_type == "EVO_HOLD_ITEM_NIGHT":
        conditions["pokemon.evolve.hasItem"] = {"string": _items.get_item_by_constant(param.removeprefix("ITEM_"))}
        conditions["pokemon.evolve.time"] = {"string": "timeOfDay.night"}
    elif evo_type == "EVO_TYPE_IN_PARTY":
        conditions["pokemon.evolve.level"] = {"number": level}
        conditions["pokemon.evolve.typedPokemonPresentInParty"] = {"string": "pokemon.type." + fields[3].removeprefix("TYPE_").lower()}
    elif evo_type == "EVO_OTHER_PARTY_MON":
        conditions["pokemon.evolve.presentInParty"] = {"string": _species_name(param.removeprefix("SPECIES_"))}
    elif evo_type == "EVO_LEVEL_ATK_GT_DEF":
        conditions["pokemon.evolve.level"] = {"number": level}
        conditions["pokemon.evolve.stat"] = {"string": "stat.attack>defense"}
    elif evo_type == "EVO_LEVEL_ATK_EQ_DEF":
        conditions["pokemon.evolve.level"] = {"number": level}
        conditions["pokemon.evolve.stat"] = {"string": "stat.attack=defense"}
    elif evo_type == "EVO_LEVEL_ATK_LT_DEF":
        conditions["pokemon.evolve.level"] = {"number": level}
        conditions["pokemon.evolve.stat"] = {"string": "stat.attack<defense"}
    elif evo_type in ("EVO_LEVEL_SILCOON", "EVO_LEVEL_CASCOON"):
        conditions["pokemon.evolve.level"] = {"number": level}
        conditions["pokemon.evolve.rarity"] = {"string": "rarity.p50Chance"}
    elif evo_type == "EVO_LEVEL_NINJASK":
        conditions["pokemon.evolve.level"] = {"number": level}
    elif evo_type == "EVO_LEVEL_SHEDINJA":
        conditions["pokemon.evolve.level"] = {"number": level}
        conditions["pokemon.evolve.emptySlot"] = {}
    elif evo_type == "EVO_FEMALE_LEVEL":
        conditions["pokemon.evolve.level"] = {"number": level}
        conditions["pokemon.evolve.gender"] = {"string": "Gender.female"}
    elif evo_type == "EVO_MALE_LEVEL":
        conditions["pokemon.evolve.level"] = {"number": level}
        conditions["pokemon.evolve.gender"] = {"string": "Gender.male"}
    elif evo_type in ("EVO_NATURE_HIGH", "EVO_NATURE_LOW"):
        conditions["pokemon.evolve.nature"] = {"string": "nature.high" if "HIGH" in evo_type else "nature.low"}
    elif evo_type == "EVO_LEVEL_SPECIFIC_TIME_RANGE":
        conditions["pokemon.evolve.level"] = {"number": level}
    else:
        conditions["pokemon.evolve.levelUp"] = {}

    return {"to": target_id, "conditions": conditions, "fromForm": 0, "toForm": 0}


def _merge_duplicate_evolutions(evo_list: list) -> list:
    """Merge evolutions sharing the same target into one entry, chaining each
    additional path under pokemon.evolve.or.nested (the app renders this as 'or')."""
    merged: list = []
    by_target: dict = {}
    for evo in evo_list:
        target = evo["to"]
        if target in by_target:
            node = by_target[target]["conditions"]
            while "pokemon.evolve.or" in node:
                node = node["pokemon.evolve.or"]["nested"]
            node["pokemon.evolve.or"] = {"nested": evo["conditions"]}
        else:
            by_target[target] = evo
            merged.append(evo)
    return merged


def process():
    print("Processing Pokedex")
    global _entries, _species_lookup, _national_id_lookup, _species_to_dex_table

    clean_species = game_strings._game_strings.get("en", {}).get("clean_species", [])
    _species_lookup = {cs.replace("_", "").lower(): cs for cs in clean_species if cs}
    _national_id_lookup = {cs: idx for idx, cs in enumerate(clean_species) if cs}
    _species_to_dex_table = _parse_species_to_dex_table()

    species_ids = _parse_species_ids()
    base_stats, constants = _parse_base_stats()
    evolutions = _parse_evolutions()

    ordered = sorted(
        ((n, sid) for n, sid in species_ids.items() if n != "NONE" and sid != 0),
        key=lambda x: x[1]
    )

    _entries = []
    base_info_by_national_id: dict = {}  # national_id -> (base_const, entry_dict)

    for species_name, species_id in ordered:
        stats = base_stats.get(species_name)
        if not stats:
            continue

        def si(key: str, default: int = 0) -> int:
            return _safe_int(stats.get(key, str(default)), constants)

        ab1 = _abilities.get_ability_by_constant(stats.get("ability1", "NONE").removeprefix("ABILITY_"))
        ab2 = _abilities.get_ability_by_constant(stats.get("ability2", "NONE").removeprefix("ABILITY_"))
        ab3 = _abilities.get_ability_by_constant(stats.get("hiddenAbility", "NONE").removeprefix("ABILITY_"))

        type1_raw = stats.get("type1", "TYPE_NORMAL")
        type2_raw = stats.get("type2", type1_raw)
        types = ["pokemon.type." + type1_raw.removeprefix("TYPE_").lower()]
        if type2_raw != type1_raw:
            types.append("pokemon.type." + type2_raw.removeprefix("TYPE_").lower())

        evo_list = []
        for evo_fields in evolutions.get(species_name, []):
            evo = _make_evolution(evo_fields, species_ids)
            if evo:
                evo_list.append(evo)
        evo_list = _merge_duplicate_evolutions(evo_list)

        national_id = _find_national_id(species_name)

        stat_block = {
            "gameId": species_id,
            "baseStats": {
                "hp": si("baseHP"),
                "atk": si("baseAttack"),
                "def": si("baseDefense"),
                "spAtk": si("baseSpAttack"),
                "spDef": si("baseSpDefense"),
                "spd": si("baseSpeed"),
            },
            "baseFriendship": si("friendship", 70),
            "evYield": {
                "hp": si("evYield_HP"),
                "atk": si("evYield_Attack"),
                "def": si("evYield_Defense"),
                "spAtk": si("evYield_SpAttack"),
                "spDef": si("evYield_SpDefense"),
                "spd": si("evYield_Speed"),
            },
            "abilities": [ab1, ab2, ab3],
            "hatchCycles": si("eggCycles"),
            "genderRatio": _gender_ratio(stats.get("genderRatio", "255")),
            "catchRate": si("catchRate", 45),
            "types": types,
            "growthRate": _GROWTH_RATE.get(stats.get("growthRate", ""), 0),
            "evolutions": evo_list,
        }

        if national_id and national_id in base_info_by_national_id:
            # Alternate form: look up the correct form index by name
            base_const, base_entry = base_info_by_national_id[national_id]
            suffix = _get_form_suffix(species_name, base_const)
            form_map = _get_national_form_map(national_id)
            form_index, strategy = _find_form_index(suffix, form_map, national_id)
            if form_index is not None:
                if strategy.startswith("fallback"):
                    print(f"\tWARNING: {species_name} matched via {strategy} — verify this is correct (available: {list(form_map.keys())})")

                # Always import from national dex form entry — no formName or name,
                # the __import provides them (also covers Mega/Primal correctly).
                form_entry = {
                    "form": form_index,
                    "__import": {f"pokelink:/pokemon/national/{national_id}.{form_index}.entry": {"FIXME_noDeepMerge": True}},
                }
                form_entry.update(stat_block)

                # Form evolutions must live on the BASE entry (with fromForm set),
                # not on the nested form entry — the app only reads the base entry's
                # evolutions list. Move them there and clear from form_entry.
                for evo in evo_list:
                    evo["fromForm"] = form_index
                base_entry.setdefault("evolutions", []).extend(evo_list)
                form_entry["evolutions"] = []

                if "forms" not in base_entry:
                    base_entry["forms"] = []
                base_entry["forms"].append(form_entry)
            else:
                # No national dex form entry matched — standalone entry with base-form sprites
                print(f"\tWARNING: {species_name} (suffix '{suffix}') not matched in national dex — available keys: {list(form_map.keys())}, using base sprite")
                entry = {
                    "id": len(_entries) + 1,
                    "name": _species_name(species_name),
                    "__import": {f"pokelink:/pokemon/national/{national_id}.entry": {"FIXME_noDeepMerge": True}},
                    **stat_block,
                }
                _entries.append(entry)
        else:
            # Base form (or unmapped species)
            if not national_id:
                print(f"\tWARNING: {species_name} has no national dex mapping, using Unown fallback")
            entry = {
                "id": len(_entries) + 1,
                "name": _species_name(species_name),
                **stat_block,
            }
            if national_id:
                entry["__import"] = {f"pokelink:/pokemon/national/{national_id}.entry": {"FIXME_noDeepMerge": True}}
                base_info_by_national_id[national_id] = (species_name, entry)
            else:
                entry["__import"] = {"pokelink:/pokemon/national/201.entry": {"FIXME_noDeepMerge": True}}
            _entries.append(entry)

    # Remap evolution targets: _make_evolution stored raw game species IDs in "to"
    # (from species.h hex values), but the app expects the sequential output "id".
    game_id_to_output_id: dict = {}
    form_game_id_to_form_idx: dict = {}
    for e in _entries:
        game_id_to_output_id[e["gameId"]] = e["id"]
    for e in _entries:
        for form_entry in e.get("forms", []):
            fgid = form_entry.get("gameId")
            if fgid is not None:
                if fgid not in game_id_to_output_id:
                    # Alt form → point to base entry so the app can reach it
                    game_id_to_output_id[fgid] = e["id"]
                form_game_id_to_form_idx[fgid] = form_entry.get("form", 0)

    def _remap_evos(evo_list: list) -> None:
        for evo in evo_list:
            raw_to = evo.get("to", 0)
            evo["to"] = game_id_to_output_id.get(raw_to, 0)
            if raw_to in form_game_id_to_form_idx:
                evo["toForm"] = form_game_id_to_form_idx[raw_to]

    for e in _entries:
        _remap_evos(e.get("evolutions", []))
        for form_entry in e.get("forms", []):
            _remap_evos(form_entry.get("evolutions", []))


def generate():
    print("Generating Pokedex")
    write_file(
        os.path.join(directories.get_output_dir("pokemon-unknown/v1.6/", True), "unknown.dex"),
        {"version": "0.7.1", "entries": _entries}
    )
