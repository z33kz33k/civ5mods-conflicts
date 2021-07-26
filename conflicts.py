"""

    conflicts.py
    ~~~~~~~~~~~~~~~~~
    Detect Civ5 mods conflicts.

    @author: z33k

"""

from collections import Counter, defaultdict
from dataclasses import dataclass
import os
from pathlib import Path
from pprint import pprint
import sys
from typing import Dict, List, Tuple


@dataclass(eq=True, frozen=True)
class LuaFile:
    path: Path
    modname: str


class Mod:
    """A Civ V mod represented by its name and all the .lua files it holds.
    """
    def __init__(self, modinfo_file: Path, *lua_files: Path) -> None:
        self.modinfo_file = modinfo_file
        self.lua_files = lua_files

    @property
    def name(self) -> str:
        return self.modinfo_file.stem


def find_conflicts(*mods: Mod) -> Tuple[Dict[str, List[Path]], Dict[str, List[Path]]]:
    """Return two dictionaries of LUA files' names mapped to a list of corresponding LuaFile objects
    (each containing two fields: path and modname). The first dict maps cases where VP .lua's
    are overwritten by at least two other mods (almost a sure conflict) and the second one maps
    other cases where at least two same .lua's come from different mods (a potential conflict).
    """
    lua_files = {LuaFile(file, mod.name) for mod in mods for file in mod.lua_files}
    d = defaultdict(list)
    for lua_file in lua_files:
        values = d.get(lua_file.path.name)
        if values is None:
            d[lua_file.path.name].append(lua_file)
        # only one lua per mod is allowed
        else:
            if lua_file.modname not in [v.modname for v in values]:
                d[lua_file.path.name].append(lua_file)

    conflictsmap, potential_conflicts_map = {}, {}
    for k, v in d.items():
        if (any(modname[0] == "(" and modname[1].isdigit() for modname in [lf.modname for lf in v])
                and len(v) >= 3):
            conflictsmap[k] = v
        elif (not any(modname[0] == "(" and modname[1].isdigit()
                      for modname in [lp.modname for lp in v]) and len(v) >= 2):
            potential_conflicts_map[k] = v

    return conflictsmap, potential_conflicts_map


def getmods(path: Path) -> List[Mod]:
    """Return mods according to the input path.
    """
    if not path.is_dir():
        raise ValueError(f"Not a directory: '{path}'.")

    dirs = [p for p in path.iterdir() if p.is_dir()]

    mods = []
    for dir_ in dirs:
        lua_files = []
        for dirpath, _, filenames in os.walk(dir_):
            for filename in filenames:
                path = Path(dirpath) / filename
                if path.suffix.lower() == ".lua":
                    lua_files.append(path)
        modinfo = next((path for path in dir_.iterdir() if path.suffix.lower() == ".modinfo"),
                       None)
        if modinfo is None:
            raise ValueError(f"Directory '{dir_}' does not contain a .modinfo file.")

        mods.append(Mod(modinfo, *lua_files))

    return mods


def print_conflicts(dir_: Path) -> None:
    """Pretty-print all detected conflicts at input directory.
    """
    mods = getmods(dir_)
    lua_files = [path for mod in mods for path in mod.lua_files]
    print(f"Parsed {len(lua_files)} .lua file(s) from {len(mods)} mod(s):")
    for i, mod in enumerate(sorted(mods, key=lambda m: m.name), start=1):
        print(f"{i}) {mod.name}")

    print()

    conflictsmap, potentialsmap = find_conflicts(*mods)
    print("Duplicates overwriting VP .lua's:")
    print("=================================")
    print()
    for item in sorted(conflictsmap.items()):
        pprint(item)

    print()
    print("Other duplicates:")
    print("=================")
    print()
    for item in sorted(potentialsmap.items()):
        pprint(item)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print_conflicts(Path(sys.argv[1]))
    else:
        print_conflicts(Path("."))
