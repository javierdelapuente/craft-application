# Copyright 2023-2024 Canonical Ltd.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Remote-build utility tests."""

import re
from pathlib import Path

import pytest
from craft_application.remote import (
    UnsupportedArchitectureError,
    get_build_id,
    humanize_list,
    rmtree,
    validate_architectures,
)
from craft_application.remote.utils import _SUPPORTED_ARCHS

###############################
# validate architecture tests #
###############################


@pytest.mark.parametrize(("archs"), [["amd64"], _SUPPORTED_ARCHS])
def test_validate_architectures(archs):
    """Validate architectures."""
    assert validate_architectures(archs) is None


@pytest.mark.parametrize(
    ("archs", "expected_archs"),
    [
        # invalid arch
        (["unknown"], ["unknown"]),
        # valid and invalid archs
        (["amd64", "unknown"], ["unknown"]),
        # multiple invalid archs
        (["unknown1", "unknown2"], ["unknown1", "unknown2"]),
        # multiple valid and invalid archs
        (["unknown1", "unknown2", "riscv64", "arm64"], ["unknown1", "unknown2"]),
    ],
)
def test_validate_architectures_error(archs, expected_archs):
    """Raise an error if an unsupported architecture is passed."""
    with pytest.raises(UnsupportedArchitectureError) as raised:
        validate_architectures(archs)

    assert (
        "The following architectures are not supported by the remote builder: "
        f"{expected_archs}"
    ) in str(raised.value)


#################
# Humanize List #
#################


@pytest.mark.parametrize(
    ("items", "conjunction", "expected"),
    [
        ([], "and", ""),
        (["foo"], "and", "'foo'"),
        (["foo", "bar"], "and", "'bar' and 'foo'"),
        (["foo", "bar", "baz"], "and", "'bar', 'baz', and 'foo'"),
        (["foo", "bar", "baz", "qux"], "and", "'bar', 'baz', 'foo', and 'qux'"),
        ([], "or", ""),
        (["foo"], "or", "'foo'"),
        (["foo", "bar"], "or", "'bar' or 'foo'"),
        (["foo", "bar", "baz"], "or", "'bar', 'baz', or 'foo'"),
        (["foo", "bar", "baz", "qux"], "or", "'bar', 'baz', 'foo', or 'qux'"),
    ],
)
def test_humanize_list(items, conjunction, expected):
    """Test humanize_list."""
    assert humanize_list(items, conjunction) == expected


def test_humanize_list_sorted():
    """Verify `sort` parameter."""
    input_list = ["z", "a", "m test", "1"]

    # unsorted list is in the same order as the original list
    expected_list_unsorted = "'z', 'a', 'm test', and '1'"

    # sorted list is sorted alphanumerically
    expected_list_sorted = "'1', 'a', 'm test', and 'z'"

    assert humanize_list(input_list, "and") == expected_list_sorted
    assert humanize_list(input_list, "and", sort=True) == expected_list_sorted
    assert humanize_list(input_list, "and", sort=False) == expected_list_unsorted


##################
# build id tests #
##################


def test_get_build_id(tmp_path):
    """Get the build id."""
    build_id = get_build_id("test-app", "test-project", tmp_path)

    assert re.match("test-app-test-project-[0-9a-f]{32}", build_id)


def test_get_build_id_is_reproducible(tmp_path):
    """The build id should be the same for the same directory."""
    path = tmp_path / "test"
    path.mkdir()

    build_id_1 = get_build_id("test-app", "test-project", path)

    (path / "some-file").write_text("Created a file")
    path.touch(mode=0o700, exist_ok=True)

    build_id_2 = get_build_id("test-app", "test-project", path)

    assert build_id_1 == build_id_2


def test_get_build_id_directory_does_not_exist_error():
    """Raise an error if the directory does not exist."""
    with pytest.raises(FileNotFoundError) as raised:
        get_build_id("test-app", "test-project", Path("/does-not-exist"))


################
# rmtree tests #
################


@pytest.fixture()
def stub_directory_tree():
    """Creates a tree of directories and files."""
    root_dir = Path("root-dir")
    (root_dir / "dir1/dir2").mkdir(parents=True, exist_ok=True)
    (root_dir / "dir3").mkdir(parents=True, exist_ok=True)
    (root_dir / "file1").touch()
    (root_dir / "dir1/file2").touch()
    (root_dir / "dir1/dir2/file3").touch()
    return root_dir


def test_rmtree(stub_directory_tree):
    """Remove a directory tree."""
    rmtree(stub_directory_tree)

    assert not Path(stub_directory_tree).exists()


def test_rmtree_readonly(stub_directory_tree):
    """Remove a directory tree that contains a read-only file."""
    (stub_directory_tree / "read-only-file").touch(mode=0o444)

    rmtree(stub_directory_tree)

    assert not Path(stub_directory_tree).exists()
