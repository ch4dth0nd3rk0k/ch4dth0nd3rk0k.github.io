"""Tests for Makefile."""

import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

import pytest
from pytest import MonkeyPatch


def get_source_makefile_path() -> Path:
    """Dynamically get the path to the source Makefile."""
    # start from the current file's directory
    current_dir = Path(__file__).resolve().parent

    # traverse upwards until you the 'Makefile' (assumed repo root)
    while current_dir.parent != current_dir:
        if (current_dir / "Makefile").exists():
            return current_dir  # found the source repository
        current_dir = current_dir.parent

    # coudln't find it
    raise FileNotFoundError(
        "Could not find the Makefile in the source repository."
    )


@lru_cache(maxsize=1)
def get_cached_makefile_path() -> Path:
    """Retrieves and caches path to the Makefile in source repository."""
    return get_source_makefile_path() / "Makefile"


def run_make(
    target: str,
    dry_mode: bool = False,
    extra_args: Optional[List[str]] = None,
    cwd: Optional[Path] = None,
    makefile_path: Optional[Path] = None,
) -> subprocess.CompletedProcess[str]:
    """Runs a Makefile target."""
    # default to source repo Makefile path if not provided
    if makefile_path is None:
        makefile_path = get_cached_makefile_path()

    # set default cwd to the current working directory if not provided
    if cwd is None:
        cwd = Path(".")

    # initial command string
    command = ["make", "-f", str(makefile_path)]

    # check for -n flag
    if dry_mode:
        command.append("-n")

    # add in target command
    command.append(target)

    # add any additional args
    if extra_args:
        command.extend(extra_args)

    # run process and get output
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)

    # done
    return result


def get_git_remote_url() -> str:
    """Helper function to get the remote URL of the repository."""
    try:
        # Run git command to get remote URL
        remote_url = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            universal_newlines=True,
        ).strip()

        # check if empy
        if not remote_url:
            return (
                "Missing `origin` remote URL: No URL set for remote 'origin'."
            )

        # normal
        return remote_url

    except subprocess.CalledProcessError:
        # Check remotes if 'origin' is missing
        try:
            remotes_list = subprocess.check_output(
                ["git", "remote", "-v"],
                universal_newlines=True,
            ).strip()

            # no origin
            return (
                "Missing `origin` remote. " f"Available remotes: {remotes_list}"
            )

        except subprocess.CalledProcessError:
            # no git repo
            return (
                "Error: Unable to fetch remote details. "
                "Ensure you are inside a valid Git repository."
            )


@pytest.fixture(scope="function")
def print_config_output() -> Dict[str, str]:
    """Fixture to get the output from the print-config target in Makefile."""
    result = run_make("print-config")

    # ensure the command ran successfully
    assert result.returncode == 0

    # parse the output from print-config and store as key-value pairs
    config_data = {}
    for line in result.stdout.splitlines():
        # only process lines with a key-value format (e.g., key: value)
        if ":" in line:
            key, value = line.split(":", 1)
            config_data[key.strip()] = value.strip()

    return config_data


@pytest.fixture(scope="function")
def current_directory(print_config_output: Dict[str, str]) -> Path:
    """Fixture to get the current dir from print-config output."""
    return Path(print_config_output["Current Directory"])


@pytest.fixture(scope="function")
def mock_blog_repo(tmp_path: Path) -> Tuple[Path, Path, Path, Path]:
    """Fixture to setup a mock blog repo."""
    # define directories
    currentdir = tmp_path
    basdir = tmp_path / "_jupyter"
    outdir = basdir / "converted"
    posts_dir = tmp_path / "_posts"
    assets_dir = tmp_path / "assets"

    # ensure necessary directories exist
    (basdir / "notebooks").mkdir(parents=True)
    (outdir / "assets" / "images").mkdir(parents=True)
    posts_dir.mkdir()
    (assets_dir / "images").mkdir(parents=True)

    return currentdir, outdir, posts_dir, assets_dir


@pytest.fixture(scope="function")
def mock_converted_files(
    mock_blog_repo: Tuple[Path, Path, Path]
) -> Tuple[Path, Path]:
    """Fixture to populate the mock blog repo with converted test files."""
    # extract paths from mock_blog_repo fixture
    currentdir, outdir, *_ = mock_blog_repo

    # setup/make post images dir
    post_images_dir = outdir / "assets" / "images" / "test_post_files"
    post_images_dir.mkdir(parents=True)

    # define file paths
    markdown_post = outdir / "test_post.md"
    post_image = post_images_dir / "test_image_001.png"
    test_notebook = currentdir / "_jupyter" / "notebooks" / "test_post.ipynb"

    # Create test files
    markdown_post.write_text("Test content for markdown file.")
    post_image.write_text("Test image content.")
    test_notebook.write_text(
        '{"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}'
    )

    return markdown_post, post_image


@pytest.fixture(scope="function")
def mock_converted_env(
    mock_blog_repo: Tuple[Path, Path, Path],
    mock_converted_files: Tuple[Path, Path],
) -> List[str]:
    """Fixture to provide environment variables for Makefile testing."""
    # extract paths from the mock_blog_repo fixture
    currentdir, outdir, *_ = mock_blog_repo

    return [f"CURRENTDIR={currentdir}", f"OUTDR={outdir}"]


@pytest.fixture(scope="function")
def mock_git_repo(
    mock_blog_repo: Tuple[Path, Path, Path, Path],
) -> Tuple[Path, Path, Path, Path]:
    """Fixture to set up a mock Git repo with untracked files."""
    # extract paths from mock_blog_repo
    currentdir, outdir, posts_dir, assets_dir = mock_blog_repo

    # initialize Git repository
    subprocess.run(["git", "init"], cwd=currentdir, check=True)

    # create a .gitignore file that ignores `_jupyter/converted/`
    gitignore_path = currentdir / ".gitignore"
    gitignore_path.write_text("_jupyter/converted/\n")

    # configure user info for git in this repository
    subprocess.run(
        ["git", "config", "user.name", "PyTest"], cwd=currentdir, check=True
    )
    subprocess.run(
        ["git", "config", "user.email", "pytest@example.com"],
        cwd=currentdir,
        check=True,
    )
    # add dummy notebook to _jupyter/notebooks
    dummy_notebook = currentdir / "_jupyter" / "notebooks" / "dummy.ipynb"
    dummy_notebook.write_text(
        '{"cells": [], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}'
    )

    # add dummy files to _posts
    dummy_post = posts_dir / "dummy.md"
    dummy_post.write_text(
        "This is a dummy file to make _posts directory tracked."
    )

    # add dummy images dir and image to assets/images
    dummy_image_dir = assets_dir / "images" / "dummy_files"
    dummy_image_dir.mkdir(parents=True)
    dummy_image = dummy_image_dir / "dummy_image.png"
    dummy_image.write_text(
        "This is a dummy image file to make assets directory tracked."
    )

    # stage .gitignore, _posts, and assets directories
    subprocess.run(
        ["git", "add", ".gitignore", "_posts", "assets", "_jupyter/notebooks"],
        cwd=currentdir,
        check=True,
    )

    # commit the changes
    subprocess.run(
        [
            "git",
            "commit",
            "-m",
            "Initial commit: setup repo structure with dummy files",
        ],
        cwd=currentdir,
        check=True,
    )

    return currentdir, outdir, posts_dir, assets_dir


@pytest.fixture(scope="function")
def mock_synced_files(
    mock_git_repo: Tuple[Path, Path, Path, Path],
    mock_converted_files: Tuple[Path, Path],
) -> Tuple[Path, Path]:
    """Fixture to sync converted files to _posts/ and assets/images/."""
    # extract paths from mock_git_repo
    _, _, posts_dir, assets_dir = mock_git_repo

    # extract converted files
    markdown_post, post_image = mock_converted_files

    # define sync destination paths
    synced_markdown = posts_dir / markdown_post.name
    synced_image_dir = assets_dir / "images" / post_image.parent.name
    synced_image = synced_image_dir / post_image.name

    # make sure the synced image dir exists
    synced_image_dir.mkdir(parents=True)

    # simulate rsync of files
    synced_markdown.write_text(markdown_post.read_text())
    synced_image.write_text(post_image.read_text())

    return synced_markdown, synced_image


@pytest.fixture(scope="function")
def mock_renamed_nb(
    mock_synced_files: Tuple[Path, Path],
    mock_blog_repo: Tuple[Path, Path, Path, Path],
) -> Path:
    """Fixture to simulate a renamed/deleted notebook, leaving a lingering post."""
    # get mock dir
    currentdir, *_ = mock_blog_repo

    # get test post
    synced_markdown, _ = mock_synced_files

    # get path to nb
    root_nb_name = synced_markdown.stem
    nb_path = currentdir / "_jupyter" / "notebooks" / f"{root_nb_name}.ipynb"

    # delete the original notebook to simulate renaming
    nb_path.unlink()

    # get renamed
    return nb_path


@pytest.fixture(scope="function")
def mock_missing_outdir(
    mock_blog_repo: Tuple[Path, Path, Path, Path]
) -> Tuple[Path, Path, Path, Path]:
    """Simulates missing output directory."""
    # get dirs
    currentdir, outdir, posts_dir, assets_dir = mock_blog_repo

    # remove outdir
    shutil.rmtree(outdir)

    # pass on all other paths
    return currentdir, outdir, posts_dir, assets_dir


@pytest.fixture(scope="function")
def mock_no_lingering_images(
    mock_blog_repo: Tuple[Path, Path, Path, Path],
    mock_converted_files: Tuple[Path, Path],
) -> Tuple[Path, Path, Path]:
    """Simulate synced files with no lingering images."""
    # extract paths from mock_git_repo
    currentdir, _, posts_dir, assets_dir = mock_blog_repo

    # extract converted files
    markdown_post, post_image = mock_converted_files

    # define sync destination paths
    synced_markdown = posts_dir / markdown_post.name
    synced_image_dir = assets_dir / "images" / post_image.parent.name
    synced_image = synced_image_dir / post_image.name

    # make sure the synced image dir exists
    synced_image_dir.mkdir(parents=True)

    # simulate rsync of files
    synced_markdown.write_text(markdown_post.read_text())
    synced_image.write_text(post_image.read_text())

    return currentdir, synced_markdown, synced_image


@pytest.fixture(scope="function")
def mock_has_lingering_images(
    mock_blog_repo: Tuple[Path, Path, Path, Path],
    mock_synced_files: Tuple[Path, Path],
) -> Tuple[Path, Path, Path]:
    """Simulate synced files with one lingering image."""
    # extract paths from repo
    currentdir, _, posts_dir, assets_dir = mock_blog_repo

    # get currentdir
    _, synced_image = mock_synced_files

    # add lingering images to assets/images
    lingering_image_dir = assets_dir / "images" / synced_image.parent.name
    lingering_image = lingering_image_dir / "lingering_image.png"
    lingering_image.write_text(
        "This is a lingering image file to make assets directory tracked."
    )

    # find all image files in the directory
    all_images = {
        img for img in (assets_dir / "images").rglob("*") if img.is_file()
    }

    # known images set
    known_images = {synced_image, lingering_image}

    # find the third image by excluding the known ones
    persisted_image = (all_images - known_images).pop()

    return currentdir, lingering_image, persisted_image


@pytest.fixture(scope="function")
def mock_has_lingering_image_dir(
    mock_blog_repo: Tuple[Path, Path, Path, Path],
) -> Tuple[Path, Path]:
    """Simulate a case with a lingering image directory."""
    # unpack mock blog repo paths
    currentdir, outdir, posts_dir, assets_dir = mock_blog_repo

    # create a fake converted markdown post in OUTDIR
    lingering_markdown = outdir / "post_with_lingering_image_dir.md"
    lingering_markdown.write_text("Post with a lingering image dir")

    # construct the expected image directory name based on the markdown name
    lingering_dir_name = f"{lingering_markdown.stem}_files"

    # create the lingering image directory in ROOT assets
    lingering_image_dir = assets_dir / "images" / lingering_dir_name
    lingering_image_dir.mkdir(parents=True)
    lingering_image = lingering_image_dir / "lingering.png"
    lingering_image.write_text("This is a fake lingering image.")

    return currentdir, lingering_image_dir


@pytest.mark.git
def test_git_installed() -> None:
    """Ensure that Git is installed and available."""
    assert shutil.which("git"), "Git is not installed or not found in PATH"


@pytest.mark.git
def test_git_remote_url() -> None:
    """Test that the git remote URL is valid and accessible."""
    remote_url = get_git_remote_url()

    # Check that the remote URL is not empty or invalid
    assert remote_url != "", "Git remote URL is empty!"

    # Check that it does not mention "Missing" unless the origin is missing
    assert (
        "Missing" not in remote_url or "origin" not in remote_url
    ), f"Unexpected missing remote: {remote_url}"

    # Check that the URL contains 'github.com'
    assert (
        "github.com" in remote_url
    ), f"Expected GitHub URL, but got: {remote_url}"


@pytest.mark.git
@pytest.mark.make
@pytest.mark.fixture
def test_no_empty_config_values(print_config_output: Dict[str, str]) -> None:
    """Test that none of the values in the print-config output are empty."""
    for value in print_config_output.values():
        assert (
            value != ""
        ), f"One of the config values is empty! Output:\n {print_config_output}"


@pytest.mark.git
@pytest.mark.make
@pytest.mark.fixture
def test_github_info_matches_docker_images(
    print_config_output: Dict[str, str]
) -> None:
    """Test that GitHub user, repo name, and branch match the Docker images."""
    # extract values
    github_user = print_config_output["GitHub User"]
    repo_name = print_config_output["Repository Name"]
    git_branch = print_config_output["Git Branch"]

    # rebuild the expected Docker image names
    expected_jupyter_image = (
        f"ghcr.io/{github_user}/{repo_name}:{git_branch}_jupyter"
    )
    expected_testing_image = (
        f"ghcr.io/{github_user}/{repo_name}:{git_branch}_testing"
    )

    # extract the actual Docker images
    jupyter_image = print_config_output["Docker Jupyter Image"]
    testing_image = print_config_output["Docker Testing Image"]

    # assert that the rebuilt Docker images match the ones in the output
    assert expected_jupyter_image == jupyter_image
    assert expected_testing_image == testing_image


@pytest.mark.git
@pytest.mark.make
def test_github_user_extraction_https() -> None:
    """Test GitHub username extraction from HTTPS URL."""
    # setup url
    remote_url = "https://github.com/User_Name/repo_name"
    result = run_make(
        "test-github-user", extra_args=[f"REMOTE_URL={remote_url}"]
    )

    # check exit value
    assert result.returncode == 0

    # cleanup output
    output = result.stdout.strip()

    # check user name
    assert output == "user_name"


@pytest.mark.git
@pytest.mark.make
def test_github_user_extraction_ssh() -> None:
    """Test GitHub username extraction from SSH URL."""
    # setup url
    remote_url = "git@github.com:User_Name/repo_name.git"
    result = run_make(
        "test-github-user", extra_args=[f"REMOTE_URL={remote_url}"]
    )

    # check exit value
    assert result.returncode == 0

    # cleaup output
    output = result.stdout.strip()

    # check user name
    assert output == "user_name"


@pytest.mark.git
@pytest.mark.make
def test_github_user_extraction_fails() -> None:
    """Test GitHub username extraction from invalid URL."""
    # setup url
    remote_url = "foo://bar@github.com/user/repo.git"
    result = run_make(
        "test-github-user", extra_args=[f"REMOTE_URL={remote_url}"]
    )

    # cleaup output
    output = result.stdout.strip()

    # error output
    assert "Invalid" in output
    assert remote_url in output


@pytest.mark.make
def test_run_make_invalid_target() -> None:
    """Confirm missing target fails."""
    # run make on missing target
    result = run_make("nonexistent_target", dry_mode=True)

    # check correct error
    assert result.returncode != 0
    assert "No rule to make target" in result.stderr


@pytest.mark.make
def test_run_make_dry_mode(monkeypatch: MonkeyPatch) -> None:
    """Test the behavior of `run_make` with dry-run mode enabled."""

    def mock_subprocess_run(
        command: List[str], *args: Tuple[Any], **kwargs: Dict[str, Any]
    ) -> subprocess.CompletedProcess[str]:
        """Mock function for subprocess.run to simulate command execution."""
        # check that "-n" (dry-run flag) is in the command list
        assert "-n" in command

        # check that the target name "build" is in the command list
        assert "build" in command

        # simulate a successful subprocess result
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    # replace subprocess.run with our mock function during the test
    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

    # call run_make with dry_mode set to True
    run_make("build", dry_mode=True)


@pytest.mark.make
def test_run_make_with_extra_args(monkeypatch: MonkeyPatch) -> None:
    """Test the `run_make` function with additional arguments."""

    def mock_subprocess_run(
        command: List[str], *args: Tuple[Any], **kwargs: Dict[str, Any]
    ) -> subprocess.CompletedProcess[str]:
        """Mock function for subprocess.run to simulate command execution."""
        # check that the extra arguments are in the command list
        assert "--jobs" in command
        assert "4" in command
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    # replace subprocess.run with our mock function during the test
    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

    # call run_make with extra_args set to ['--jobs', '4']
    run_make("build", extra_args=["--jobs", "4"])


@pytest.mark.make
def test_check_docker_dry_run() -> None:
    """Test `check-docker` make target executes the expected command."""
    result = run_make("check-docker", dry_mode=True)

    # verify that the expected command appears in the dry run output
    assert "docker --version" in result.stdout
    assert result.returncode == 0


@pytest.mark.make
def test_check_deps_tests_without_notty_defined() -> None:
    """Test that NOTTY is correctly handled when not set."""
    result = run_make("check-deps-tests", dry_mode=True)
    assert result.returncode == 0
    assert "-it" in result.stdout  # Ensure -it is included


@pytest.mark.make
def test_check_deps_tests_with_notty() -> None:
    """Test that NOTTY is correctly handled in check-deps-tests."""
    result = run_make(
        "check-deps-tests", extra_args=["NOTTY=true"], dry_mode=True
    )
    assert result.returncode == 0
    assert "-i" in result.stdout
    assert "-it" not in result.stdout  # Ensure -it is not included


@pytest.mark.make
def test_check_deps_tests_without_notty() -> None:
    """Test that NOTTY is correctly handled when false."""
    result = run_make(
        "check-deps-tests", extra_args=["NOTTY=false"], dry_mode=True
    )
    assert result.returncode == 0
    assert "-it" in result.stdout  # Ensure -it is included


@pytest.mark.make
def test_build_jupyter_no_options() -> None:
    """Test build-jupyter target without DCKR_PULL or DCKR_NOCACHE options."""
    result = run_make("build-jupyter", dry_mode=True)

    # Check that docker pull/build is in command, but no --no-cache flag
    assert "docker pull" in result.stdout
    assert "docker build" in result.stdout
    assert "--no-cache" not in result.stdout


@pytest.mark.make
def test_build_jupyter_with_nocache() -> None:
    """Test the build-jupyter target with DCKR_NOCACHE option."""
    result = run_make(
        "build-jupyter", dry_mode=True, extra_args=["DCKR_NOCACHE=true"]
    )

    # Check that --no-cache flag is passed to docker build
    assert "docker build" in result.stdout
    assert "--no-cache" in result.stdout
    assert "docker pull" in result.stdout


@pytest.mark.make
def test_build_jupyter_with_no_pull() -> None:
    """Test build-jupyter target with no DCKR_PULL."""
    result = run_make(
        "build-jupyter", dry_mode=True, extra_args=["DCKR_PULL=false"]
    )

    # check that docker pull not included in the output
    assert "DCKR_PULL=false" in result.stdout
    assert "--no-cache" not in result.stdout


@pytest.mark.make
def test_build_tests_no_options() -> None:
    """Test build-tests target without DCKR_PULL or DCKR_NOCACHE options."""
    result = run_make("build-tests", dry_mode=True)

    # Check that docker pull/build is in command, but no --no-cache flag
    assert "docker pull" in result.stdout
    assert "docker build" in result.stdout
    assert "--no-cache" not in result.stdout


@pytest.mark.make
def test_build_tests_with_nocache() -> None:
    """Test the build-tests target with DCKR_NOCACHE option."""
    result = run_make(
        "build-tests", dry_mode=True, extra_args=["DCKR_NOCACHE=true"]
    )

    # Check that --no-cache flag is passed to docker build
    assert "docker build" in result.stdout
    assert "--no-cache" in result.stdout
    assert "docker pull" in result.stdout


@pytest.mark.make
def test_build_tests_with_no_pull() -> None:
    """Test build-tests target with no DCKR_PULL."""
    result = run_make(
        "build-tests", dry_mode=True, extra_args=["DCKR_PULL=false"]
    )

    # check that docker pull not included in the output
    assert "DCKR_PULL=false" in result.stdout
    assert "--no-cache" not in result.stdout


@pytest.mark.make
def test_use_vol_default() -> None:
    """Test that volume is mounted by default."""
    # run the make command with default environment (USE_VOL=true)
    result = run_make("pytest", dry_mode=True)

    # assert that the expected flag "-v" is present in the result
    assert result.returncode == 0
    assert "-v" in result.stdout


@pytest.mark.make
def test_use_vol_off(current_directory: Path) -> None:
    """Test that volume is mounted by default."""
    # run the make command with default environment (USE_VOL=true)
    result = run_make("pytest", dry_mode=True, extra_args=["USE_VOL=false"])

    # assert that the expected flag "-v" is present in the result
    assert result.returncode == 0
    assert "-v" not in result.stdout
    assert str(current_directory) not in result.stdout


@pytest.mark.make
def test_use_usr_default() -> None:
    """Test that `--user` is enabled by default in the Makefile."""
    # Run the make command with default environment (USE_USR=true)
    result = run_make("pytest", dry_mode=True)

    # Assert that the expected flag "-u" is present in the result
    assert "--user" in result.stdout


@pytest.mark.make
def test_use_usr_off() -> None:
    """Test that `--user` is missing with USE_USR=false."""
    # Run the make command with default environment (USE_USR=true)
    result = run_make("pytest", dry_mode=True, extra_args=["USE_USR=false"])

    # Assert that the expected flag "-u" is present in the result
    assert "--user" not in result.stdout


@pytest.mark.make
def test_mock_blog_repo(mock_blog_repo: Tuple[Path, Path, Path, Path]) -> None:
    """Test that mock_blog_repo correctly creates required directories."""
    currentdir, outdir, posts_dir, assets_dir = mock_blog_repo

    # Ensure directories exist
    assert currentdir.exists(), "Current directory does not exist"
    assert outdir.exists(), "Output directory does not exist"
    assert posts_dir.exists(), "_posts directory does not exist"
    assert (
        assets_dir / "images"
    ).exists(), "Assets images directory does not exist"
    assert (
        outdir / "assets" / "images"
    ).exists(), "Converted assets/images directory does not exist"


@pytest.mark.make
def test_mock_converted_files(
    mock_converted_files: Tuple[Path, Path],
) -> None:
    """Test that mock converted files correctly creates test files."""
    markdown_post, post_image = mock_converted_files

    # Ensure files exist
    assert markdown_post.exists(), "Markdown post file was not created"
    assert post_image.exists(), "Post image file was not created"


@pytest.mark.make
def test_mock_converted_env(
    mock_blog_repo: Tuple[Path, Path, Path, Path],
    mock_converted_env: List[str],
) -> None:
    """Test that mock_converted_env correctly returns environment variables."""
    currentdir, outdir, *_ = mock_blog_repo

    # Ensure environment variables are set correctly
    assert (
        f"CURRENTDIR={currentdir}" in mock_converted_env
    ), "CURRENTDIR not set correctly"
    assert f"OUTDR={outdir}" in mock_converted_env, "OUTDR not set correctly"


@pytest.mark.make
def test_basic_sync(
    mock_blog_repo: Tuple[Path, Path, Path],
    mock_converted_files: Tuple[Path, Path],
    mock_converted_env: List[str],
) -> None:
    """Test the 'sync' Makefile target using mock blog repo."""
    *_, posts_dir, assets_dir = mock_blog_repo
    markdown_post, post_image = mock_converted_files

    # Run Makefile 'sync' command
    result = run_make("sync", extra_args=mock_converted_env)

    # Validate that the markdown file was moved to _posts/
    assert (
        posts_dir / markdown_post.name
    ).exists(), "Markdown file was not moved to _posts"

    # Validate that the image file was moved to assets/images/
    assert (
        assets_dir / "images" / post_image.parent.name / post_image.name
    ).exists(), "Image file was not moved to assets/images"

    # Check expected output logs
    assert (
        "Moving all jupyter" in result.stdout
    ), "Expected log output not found"


@pytest.mark.make
def test_mock_git_repo(mock_git_repo: Tuple[Path, Path, Path, Path]) -> None:
    """Test that the mock Git repo is correctly initialized."""
    # get the currend temp dir
    currentdir, _, _, _ = mock_git_repo

    # ensure .git directory exists
    assert (currentdir / ".git").exists(), "Git repository was not initialized."

    # ensure .gitignore exists ...
    gitignore_path = currentdir / ".gitignore"
    assert gitignore_path.exists(), ".gitignore file was not created."

    # ... and contains expected content
    gitignore_content = gitignore_path.read_text().strip()
    assert (
        "_jupyter/converted/" in gitignore_content
    ), ".gitignore rule is missing."

    # ensure `git status` runs without error
    result = subprocess.run(
        ["git", "status"], cwd=currentdir, capture_output=True, text=True
    )
    assert (
        result.returncode == 0
    ), "Git repository is not functioning correctly."


@pytest.mark.make
def test_check_renamed_no_changes(
    mock_synced_files: Tuple[Path, Path],
    mock_blog_repo: Tuple[Path, Path, Path, Path],
) -> None:
    """Test that check-renamed does nothing when no renamed notebooks exist."""
    # get mock dir
    currentdir, *_ = mock_blog_repo

    # run
    result = run_make("check-renamed-posts", cwd=currentdir)

    # check code
    assert (
        result.returncode == 0
    ), f"Expected exit code 0, but got {result.returncode}."

    # get synced files
    synced_markdown, _ = mock_synced_files

    # check
    assert "No untracked posts found" in result.stdout
    assert str(synced_markdown) not in result.stdout


@pytest.mark.make
def test_check_renamed_detects_lingering(
    mock_renamed_nb: Path,
    mock_blog_repo: Tuple[Path, Path, Path, Path],
) -> None:
    """Test check-renamed detects lingering posts when notebook is renamed."""
    # get mock dir
    currentdir, _, _, _ = mock_blog_repo

    # get markdown post without notebook
    lingering_post = f"{mock_renamed_nb.stem}.md"

    # run
    result = run_make("check-renamed-posts", cwd=currentdir)

    # check code
    assert (
        result.returncode == 0
    ), f"Expected exit code 0, but got {result.returncode}."

    # check
    assert "Untracked posts found" in result.stdout
    assert "make clear-renamed" in result.stdout
    assert lingering_post in result.stdout


@pytest.mark.make
def test_clear_renamed_no_changes(
    mock_synced_files: Tuple[Path, Path],
    mock_blog_repo: Tuple[Path, Path, Path, Path],
) -> None:
    """Test that clear-renamed does nothing when no renamed notebooks exist."""
    # get mock dir
    currentdir, *_ = mock_blog_repo

    # run
    result = run_make("clear-renamed-posts", cwd=currentdir)

    # check code
    assert (
        result.returncode == 0
    ), f"Expected exit code 0, but got {result.returncode}."

    # get synced files
    synced_markdown, _ = mock_synced_files

    # check
    assert "No untracked posts" in result.stdout
    assert "Removed untracked" not in result.stdout
    assert str(synced_markdown) not in result.stdout


@pytest.mark.make
def test_clear_renamed_with_lingering_posts_and_images(
    mock_renamed_nb: Path,
    mock_blog_repo: Tuple[Path, Path, Path, Path],
    mock_synced_files: Tuple[Path, Path],
) -> None:
    """Test that clear-renamed removes lingering posts and images dir."""
    # get the current directory and mock paths
    currentdir, _, posts_dir, assets_dir = mock_blog_repo

    # get synced files
    synced_markdown, _ = mock_synced_files

    # simulate the lingering renamed post and image directory
    post_name = f"{mock_renamed_nb.stem}.md"
    image_dir = assets_dir / "images" / f"{synced_markdown.stem}_files"

    # verify the image directory exists before running the command
    assert (
        image_dir.exists()
    ), f"Image directory {image_dir} should exist before cleanup"

    # run
    result = run_make("clear-renamed-posts", cwd=currentdir)

    # check code
    assert (
        result.returncode == 0
    ), f"Expected exit code 0, but got {result.returncode}."

    # verify that the lingering post was deleted
    assert (
        not synced_markdown.exists()
    ), f"Post {synced_markdown} should be deleted"
    assert str(post_name) in result.stdout
    assert "Removed untracked post" in result.stdout

    # verify that the corresponding image directory was deleted
    assert (
        not image_dir.exists()
    ), f"Image directory {image_dir} should be deleted"
    assert str(image_dir.stem) in result.stdout
    assert "Removed corresponding image directory" in result.stdout

    # check that the command output contains the cleanup success message
    assert (
        "Cleanup complete." in result.stdout
    ), f"Expected 'Cleanup complete.' in output but got {result.stdout}"


@pytest.mark.make
def test_check_renamed_images_missing_outdir(
    mock_missing_outdir: Tuple[Path, Path, Path, Path]
) -> None:
    """Test when the _jupyter/converted directory is missing."""
    # get the current directory and mock paths
    currentdir, *_ = mock_missing_outdir

    # run
    result = run_make("check-renamed-images", cwd=currentdir)

    # make sure it failed
    assert result.returncode != 0
    assert "⚠️ Warning" in result.stdout


@pytest.mark.make
def test_clear_renamed_images_missing_outdir(
    mock_missing_outdir: Tuple[Path, Path, Path, Path]
) -> None:
    """Test when the _jupyter/converted directory is missing."""
    # get the current directory and mock paths
    currentdir, *_ = mock_missing_outdir

    # run
    result = run_make("clear-renamed-images", cwd=currentdir)

    # make sure it failed
    assert result.returncode != 0
    assert "⚠️ Warning" in result.stdout


@pytest.mark.make
def test_check_renamed_images_no_lingering(
    mock_no_lingering_images: Tuple[Path, Path, Path],
) -> None:
    """Test that no warnings appear when there are no lingering images."""
    # Get the current directory
    currentdir, _, synced_image = mock_no_lingering_images

    # Run the check-renamed-images command
    result = run_make("check-renamed-images", cwd=currentdir)

    # Ensure it ran successfully and no warnings were issued
    assert (
        result.returncode == 0
    ), f"Code: {result.returncode}. Output: {result.stdout}"

    assert (
        synced_image.name not in result.stdout
    ), f"{synced_image.name!r} found in the output: {result.stdout}"

    assert (
        "❌ Lingering image detected" not in result.stdout
    ), f"Lingering image detected' in the output: {result.stdout}"

    assert (
        "🗑️ Removed lingering image" not in result.stdout
    ), f"'Removed lingering image' in the output: {result.stdout}"

    assert (
        "Checking renamed or lingering images" in result.stdout
    ), "Expected to find 'Checking renamed or lingering images' in the output."


@pytest.mark.make
def test_clear_renamed_images_no_lingering(
    mock_no_lingering_images: Tuple[Path, Path, Path],
) -> None:
    """Test that no warnings appear when there are no lingering images."""
    # Get the current directory
    currentdir, _, synced_image = mock_no_lingering_images

    # Run the clear-renamed-images command
    result = run_make("clear-renamed-images", cwd=currentdir)

    # Ensure it ran successfully and no warnings were issued
    assert (
        result.returncode == 0
    ), f"Code: {result.returncode}. Output: {result.stdout}"

    assert (
        synced_image.name not in result.stdout
    ), f"{synced_image.name!r} found in the output: {result.stdout}"

    assert (
        "❌ Lingering image detected" not in result.stdout
    ), f"Lingering image detected' in the output: {result.stdout}"

    assert (
        "🗑️ Removed lingering image" not in result.stdout
    ), f"'Removed lingering image' in the output: {result.stdout}"

    assert (
        "Clearing renamed or lingering images" in result.stdout
    ), "Expected to find 'Checking renamed or lingering images' in the output."


@pytest.mark.make
def test_check_renamed_images_has_lingering(
    mock_has_lingering_images: Tuple[Path, Path, Path],
) -> None:
    """Test that warnings do appear when there are lingering images."""
    # Get the current directory
    currentdir, lingering_image, persisted_image = mock_has_lingering_images

    # Run the check-renamed-images command
    result = run_make("check-renamed-images", cwd=currentdir)

    # Ensure it ran successfully and no warnings were issued
    assert (
        result.returncode == 0
    ), f"Code: {result.returncode}. Output: {result.stdout}"

    # confirm correct files untouched
    assert lingering_image.exists()
    assert persisted_image.exists()

    assert (
        lingering_image.name in result.stdout
    ), f"{lingering_image.name!r} not found in the output: {result.stdout}"

    assert (
        "❌ Lingering image detected" in result.stdout
    ), f"Lingering image detected' no found in output: {result.stdout}"

    assert (
        "🗑️ Removed lingering image" not in result.stdout
    ), f"'Removed lingering image' in the output: {result.stdout}"

    assert (
        "Checking renamed or lingering images" in result.stdout
    ), "Expected to find 'Checking renamed or lingering images' in the output."


@pytest.mark.make
def test_clear_renamed_images_has_lingering(
    mock_has_lingering_images: Tuple[Path, Path, Path],
) -> None:
    """Test that lingering images are removed."""
    # Get the current directory
    currentdir, lingering_image, persisted_image = mock_has_lingering_images

    # Run the check-renamed-images command
    result = run_make("clear-renamed-images", cwd=currentdir)

    # Ensure it ran successfully and no warnings were issued
    assert (
        result.returncode == 0
    ), f"Code: {result.returncode}. Output: {result.stdout}"

    # confirm correct files deleted
    assert not lingering_image.exists()
    assert persisted_image.exists()

    assert (
        lingering_image.name in result.stdout
    ), f"{lingering_image.name!r} not found in the output: {result.stdout}"

    assert (
        "❌ Lingering image detected" not in result.stdout
    ), f"Lingering image detected' no found in output: {result.stdout}"

    assert (
        "🗑️ Removed lingering image" in result.stdout
    ), f"'Removed lingering image' in the output: {result.stdout}"

    assert (
        "Clearing renamed or lingering images" in result.stdout
    ), "Expected to find 'Checking renamed or lingering images' in the output."


@pytest.mark.make
def test_check_lingering_image_dir(
    mock_has_lingering_image_dir: Tuple[Path, Path]
) -> None:
    """Test that a lingering image directory is detected in checking mode."""
    currentdir, lingering_image_dir = mock_has_lingering_image_dir

    result = run_make("check-renamed-images", cwd=currentdir)

    assert (
        result.returncode == 0
    ), f"Code: {result.returncode}. Output: {result.stdout}"

    assert (
        "❌ Lingering image directory detected" in result.stdout
    ), f"Missing warning for lingering image dir in: {result.stdout}"
    assert lingering_image_dir.exists()


@pytest.mark.make
def test_clear_lingering_image_dir(
    mock_has_lingering_image_dir: Tuple[Path, Path]
) -> None:
    """Test that a lingering image directory is deleted in clearing mode."""
    currentdir, lingering_image_dir = mock_has_lingering_image_dir

    result = run_make("clear-renamed-images", cwd=currentdir)

    assert (
        result.returncode == 0
    ), f"Code: {result.returncode}. Output: {result.stdout}"

    assert (
        "🗑️ Removed obsolete image directory" in result.stdout
    ), f"Expected image dir removal message in: {result.stdout}"
    assert not lingering_image_dir.exists()


@pytest.mark.make
def test_mock_synced_files(mock_synced_files: Tuple[Path, Path]) -> None:
    """Test that files were correctly synced to _posts/ and assets/images/."""
    # get synced files
    synced_markdown, synced_image = mock_synced_files

    assert synced_markdown.exists(), "Markdown file was not synced correctly."
    assert synced_image.exists(), "Image file was not synced correctly."


@pytest.mark.make
def test_unsync(
    mock_blog_repo: Tuple[Path, Path, Path, Path],
    mock_synced_files: Tuple[Path, Path],
    mock_converted_env: List[str],
) -> None:
    """Test 'unsync' for removing files from _posts and assets/images."""
    # get currentdir
    currentdir, *_ = mock_blog_repo

    # extract directories and synced files
    synced_markdown, synced_image = mock_synced_files

    # run Makefile 'unsync' command
    result = run_make("unsync", extra_args=mock_converted_env, cwd=currentdir)

    # check code
    assert (
        result.returncode == 0
    ), f"Expected exit code 0, but got {result.returncode}."

    # check that the files were removed from _posts and assets/images
    assert (
        not synced_markdown.exists()
    ), "Synced markdown file should be removed after unsync."
    assert (
        not synced_image.exists()
    ), "Synced image file should be removed after unsync."

    # check expected log output for file removal
    assert (
        "Removed ->" in result.stdout
    ), "Expected log output not found for file removal."
    assert (
        "Unsyncing complete." in result.stdout
    ), "Expected 'Unsyncing complete.' message not found."


@pytest.mark.make
def test_check_workdir_matches_dckrsrc(
    print_config_output: Dict[str, str]
) -> None:
    """Test that the working directory inside the container matches DCKRSRC."""
    # set the expected working directory
    expected_workdir = (
        f"/usr/local/src/{print_config_output['Repository Name']}"
    )

    # pull actual DCKRSRC from config output
    actual_workdir = print_config_output["Docker Source Path"]

    # make sure they match
    assert expected_workdir == actual_workdir
