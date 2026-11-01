"""The agent tree's own layout, read by looking: which directories are packages, which packages a package's code
imports, what an image of some of them keeps, and the build's step that lays an image's source out."""

from __future__ import annotations

from pathlib import Path

from agent.tree import closed, dependency_files, kept, lay_out, packages

ROOT = Path(__file__).resolve().parents[2]
KERNEL = ROOT / "agent"


def test_a_package_is_a_directory_holding_an_ontology_and_a_family_holds_packages():
    found = packages(KERNEL)
    assert {"belief", "planning", "sensing", "transport/mqtt", "transport/telegram"} <= set(found)
    assert "transport" not in found and "history" not in found and "metrics" not in found, "a family, and the watchers"


def test_a_package_is_closed_over_the_packages_its_code_imports():
    assert closed(["planning"], KERNEL) == ["belief", "execution", "planning"], "planning runs belief's machine"
    assert closed(["sensing"], KERNEL) == ["sensing"]


def test_an_image_keeps_the_kernel_its_families_own_files_and_the_packages_named_alone():
    held = kept(["sensing", "transport/mqtt"], KERNEL)
    assert {"runtime.py", "store.py", "ontology.ttl", "tree.py", "history", "metrics", "sensing",
            "transport/transport.py", "transport/mqtt"} <= set(held)
    assert not {"planning", "belief", "transport/http", "transport/telegram"} & set(held), "no package it was not named"
    assert not [h for h in held if h.endswith("tests") or h.endswith("conftest.py")], "the runner's, never the agent's"


def test_the_build_lays_out_the_kept_trees_and_the_dependency_files_of_what_the_image_holds(tmp_path):
    lay_out(ROOT, tmp_path, ["belief", "sensing"], simulator=False)
    trees, deps = tmp_path / "trees", tmp_path / "deps"
    assert (trees / "agent" / "belief").is_dir() and (trees / "agent" / "runtime.py").is_file()
    assert not (trees / "agent" / "planning").exists() and not (trees / "simulation").exists()
    assert (trees / "domains").is_dir() and not (trees / "onboarding").exists()
    assert (deps / "pyproject.toml").is_file() and (deps / "agent" / "belief" / "dependencies.txt").is_file()
    assert not (deps / "onboarding").exists() and not (deps / "agent" / "transport").exists(), \
        "the dependency files of what it holds alone; setuptools passes over the rest"
    assert set(dependency_files(ROOT / "pyproject.toml")) >= {"belief", "transport-mqtt", "series", "onboarding"}
