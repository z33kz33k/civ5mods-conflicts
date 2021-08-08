"""

    conflicts.py
    ~~~~~~~~~~~~~~~~~
    Detect Civ5 mods conflicts.

    @author: z33k

"""
from collections import defaultdict
from dataclasses import dataclass
import os
from pathlib import Path
from pprint import pprint
import sys
from typing import DefaultDict, Dict, List, Set, Tuple


VP_MODNAMES = [
    "(1) Community Patch",
    "(2) Community Balance Overhaul",
    "(3) CSD for CBP",
    "(4) Civ IV Diplomatic Features",
    "(5) More Luxuries",
    "(6a) Community Balance Overhaul - Compatibility Files (EUI)",
    "(6b) Community Balance Overhaul - Compatibility Files (No-EUI)",
    "(6c) 43 Civs CP",
    "(7a) Promotion Icons for VP",
    "(7b) UI - Promotion Tree for VP",
]


@dataclass(eq=True, frozen=True)
class LuaFile:
    path: Path
    modname: str
    is_vp: bool


class Mod:
    """A Civ V mod represented by its name and all the .lua files it holds.
    """
    def __init__(self, modinfo_file: Path, *lua_files: Path) -> None:
        self.modinfo_file = modinfo_file
        self.lua_files = lua_files

    @property
    def name(self) -> str:
        return self.modinfo_file.stem


def is_voxpopuli(modname: str) -> bool:
    """Return True if modname is a VP mode's name.

    NOTE: modname (name of a .modinfo file) is usually longer than the actual mod's name (because
    it appends a version info) - that's why the containment check has the direction as follows.
    """
    return any(vpname in modname for vpname in VP_MODNAMES)


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


def sort_out_luas(*mods: Mod) -> Tuple[Set[LuaFile], Set[LuaFile]]:
    """Sort out LUA files in mods into VP ones and not-VP ones.
    """
    lua_files = {LuaFile(file, mod.name, False) for mod in mods for file in mod.lua_files}
    vp_lua_files = {LuaFile(lf.path, lf.modname, True) for lf in lua_files
                    if is_voxpopuli(lf.modname)}
    not_vp_lua_files = {lf for lf in lua_files if not is_voxpopuli(lf.modname)}
    return vp_lua_files, not_vp_lua_files


def _add_lua(duplimap: DefaultDict[str, List[LuaFile]], lua: LuaFile) -> None:
    """Add lua to duplimap.
    """
    values = duplimap.get(lua.path.name)
    if values is None:
        duplimap[lua.path.name].append(lua)
    # only one instance of a particular lua's name per mod is allowed
    else:
        if lua.modname not in [v.modname for v in values]:
            duplimap[lua.path.name].append(lua)


def find_vp_conflicts(vp_luas: Set[LuaFile],
                      not_vp_luas: Set[LuaFile]) -> Dict[str, List[Path]]:
    """Return a dictionary of LUA files' names mapped to a list of corresponding LuaFile objects
    (each containing two fields: path and modname). The dict maps cases where VP .lua's are
    overwritten by at least two other mods (almost a sure conflict).
    """
    d = defaultdict(list)
    for lua in vp_luas:
        d[lua.path.name].append(lua)
    for lua in not_vp_luas:
        _add_lua(d, lua)

    return {k: v for k, v in d.items() if any(lf in vp_luas for lf in v) and len(v) >= 3}


def find_not_vp_conflicts(not_vp_luas: Set[LuaFile]) -> Dict[str, List[Path]]:
    """Return a dictionary of LUA files' names mapped to a list of corresponding LuaFile objects
    (each containing two fields: path and modname). The dict maps cases where at least two same
    not-VP .lua's come from different mods (a potential conflict).
    """
    d = defaultdict(list)
    for lua in not_vp_luas:
        _add_lua(d, lua)

    return {k: v for k, v in d.items() if len(v) >= 2}


def print_conflicts(dir_: Path) -> None:
    """Pretty-print all detected conflicts at input directory.
    """
    mods = getmods(dir_)
    lua_files = [path for mod in mods for path in mod.lua_files]
    print(f"Parsed {len(lua_files)} .lua file(s) from {len(mods)} mod(s):")
    for i, mod in enumerate(sorted(mods, key=lambda m: m.name), start=1):
        print(f"{i}) {mod.name}")
    print()

    vp_luas, not_vp_luas = sort_out_luas(*mods)
    vp_conflicts_map = find_vp_conflicts(vp_luas, not_vp_luas)
    not_vp_conflicts_map = find_not_vp_conflicts(not_vp_luas)

    print("Duplicates overwriting VP .lua's:")
    print("=================================")
    print()
    for item in sorted(vp_conflicts_map.items()):
        pprint(item)

    print()
    print("Other duplicates:")
    print("=================")
    print()
    for item in sorted(not_vp_conflicts_map.items()):
        pprint(item)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print_conflicts(Path(sys.argv[1]))
    else:
        print_conflicts(Path("."))
