"""Tests for website."""

import filecmp
import os
import random
import shutil
import subprocess
import time
import warnings
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Dict
from typing import Generator
from typing import List
from typing import Set
from typing import Tuple
from urllib.parse import urljoin
from urllib.parse import urlparse
from urllib.parse import urlunparse

import pytest
import requests
import yaml
from bs4 import BeautifulSoup
from PIL import Image
from pytest import TempPathFactory
from selenium.webdriver.common.by import By
from seleniumbase import BaseCase

from tests.jekyll_server import JekyllServer
from tests.jekyll_server import SimpleHTTPServer
from tests.jekyll_server import run_jekyll_build


def get_project_directory() -> Path:
    """Get project directory path object."""
    # get the path of the current file (test_file.py)
    current_file_path = Path(os.path.abspath(__file__))

    # get grand parent dir
    return current_file_path.parents[1]


def clone_directory(src: Path, dst: Path, ignore_dirs: Set[str]) -> None:
    """Clone a directory recursively to another location."""
    # ensure the destination directory exists
    if not dst.exists():
        dst.mkdir(parents=True)

    # copy everything in the source directory to the destination
    shutil.copytree(
        src,
        dst,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(*ignore_dirs),
    )


def compare_directories(
    src: Path, dst: Path, ignore_dirs: Set[str]
) -> List[Tuple[Path, Path]]:
    """Recursively compare two dirs and return diff while ignoring key dirs."""
    # container for any diffs found
    differences = []

    # compare files in the current directory
    comparison = filecmp.dircmp(src, dst)

    # ignore the specified directories at the root level
    left_only_filtered = [
        f for f in comparison.left_only if f not in ignore_dirs
    ]
    right_only_filtered = [
        f for f in comparison.right_only if f not in ignore_dirs
    ]

    # check for differing files
    for file in comparison.diff_files:
        differences.append((src / file, dst / file))

    # check for files only in src (i.e., missing in dst)
    for file in left_only_filtered:
        differences.append((src / file, dst / file))

    # check for files only in dst (i.e., extra in dst)
    for file in right_only_filtered:
        differences.append((src / file, dst / file))

    # check subdirectories
    for subdir_name, subdir_cmp in comparison.subdirs.items():
        # ignore subdirs if in ignored dirs
        if subdir_name not in ignore_dirs:
            # get diffs again
            subdir_differences = compare_directories(
                Path(subdir_cmp.left), Path(subdir_cmp.right), ignore_dirs
            )

            # diffs found ...
            if subdir_differences:
                # add to dirs with diffs
                differences.append(
                    (Path(subdir_cmp.left), Path(subdir_cmp.right))
                )

                # then add their content's diffs
                differences.extend(subdir_differences)

    return differences


def generate_image(
    width: int = 100, height: int = 100, seed: int = 42
) -> Image.Image:
    """Generates a deterministic in-memory black-and-white JPG image."""
    # ensure deterministic output
    random.seed(seed)

    # "L" mode for grayscale (black and white)
    img = Image.new("L", (width, height))

    # load pixels
    pixels = img.load()

    # check pixels loaded correctly
    if pixels is None:
        raise ValueError("Failed to load image pixels.")

    # generate random but deterministic grayscale value
    for x in range(width):
        for y in range(height):
            # random gray value between 0 and 255
            pixels[x, y] = random.randint(0, 255)

    return img


def markdown_post_data() -> Dict[str, str]:
    """Define the data for the markdown post."""
    return {
        "layout": "article",
        "title": "Test Post",
        "custom_css": "article.css",
        "include_mathjax": "false",
        "image_ref": "[No Image]",
        "content": (
            "## This is a test post\n"
            "This is a sample post for testing purposes."
        ),
    }


def generate_markdown_post(
    data_func: Callable[[], Dict[str, str]] = markdown_post_data
) -> str:
    """Generates basic Markdown post without an image reference."""
    # get markdown data
    data = data_func()

    # store content without indentation
    content = [
        "---",
        f"layout: {data['layout']}",
        f"title: {data['title']}",
        f"custom_css: {data['custom_css']}",
        f"include_mathjax: {data['include_mathjax']}",
        "---",
        "",
        f"{data['image_ref']}",
        "",
        f"{data['content']}",
    ]

    return "\n".join(content)


def swap_protocol_and_domain(original_url: str, new_full_domain: str) -> str:
    """Swap the protocol (scheme) and domain (netloc) of the given URL."""
    # Parse the original URL and the new domain URL
    parsed_original_url = urlparse(original_url)
    parsed_new_domain = urlparse(new_full_domain)

    # Replace the protocol (scheme) and domain (netloc)
    new_url = parsed_original_url._replace(
        scheme=parsed_new_domain.scheme, netloc=parsed_new_domain.netloc
    )

    # Reassemble and return the new URL
    return urlunparse(new_url)


def remove_html_extension(url: str) -> str:
    """Removes the .html extension from the URL if it exists."""
    if url.endswith(".html"):
        return url[:-5]
    return url


@pytest.fixture(scope="session")
def project_dir() -> Path:
    """Get the path of the project directory."""
    return get_project_directory()


@pytest.fixture(scope="session")
def ignore_dirs() -> Set[str]:
    """Create set of all dirs to ignore."""
    return {
        "_site",
        ".git",
        ".github",
        ".jekyll-cache",
        ".mypy_cache",
        ".pytest_cache",
    }


@pytest.fixture(scope="function")
def temp_project_dir(
    tmp_path: Path, project_dir: Path, ignore_dirs: Set[str]
) -> Path:
    """Create a temporary directory to copy the source files for testing."""
    # create new temp web src dir
    tmp_src = tmp_path / "web_src_function"
    tmp_src.mkdir(parents=True)

    # now clone
    clone_directory(project_dir, tmp_src, ignore_dirs)

    # get tmp src path
    return tmp_src


@pytest.fixture(scope="function")
def jekyll_user_config(temp_project_dir: Path) -> Dict[str, Any]:
    """Fixture for Jekyll _config.yml as a dictionary."""
    # set path
    config_path = temp_project_dir / "_config.yml"

    # check if the _config.yml file exists in the working directory
    if not config_path.exists():
        raise FileNotFoundError(f"{config_path} not found.")

    # open and read the file
    with open(config_path, "r") as file:
        config: Dict[str, Any] = yaml.safe_load(file)

    return config


@pytest.fixture(scope="function")
def comp_dirs_test_data(tmp_path: Path) -> Tuple[Path, Path]:
    """Create temporary directories for testing and return source and destination."""
    # create a source directory
    src = tmp_path / "source"
    src.mkdir()

    # create some files in the source directory
    (src / "file1.txt").write_text("file1 content")
    (src / "file2.txt").write_text("file2 content")
    (src / "subdir").mkdir()
    (src / "subdir" / "file3.txt").write_text("file3 content")

    # create a destination directory, and copy contents from the source
    dst = tmp_path / "destination"
    shutil.copytree(src, dst)

    # modify a file in the destination to create a difference
    (dst / "file2.txt").write_text("modified file2 content")

    # delete a file in the destination to create a difference
    (dst / "subdir" / "file3.txt").unlink()

    # create an extra file in the destination
    (dst / "file4.txt").write_text("extra file in destination")

    return src, dst


@pytest.fixture(scope="function")
def jekyll_server(
    temp_project_dir: Path,
) -> Generator[JekyllServer, None, None]:
    """Fixture to create a JekyllServer instance, with auto cleanup after the test."""
    # get instance
    server = JekyllServer(cwd=temp_project_dir)

    # start the server before the test
    server.start()

    # yield the server instance to the test
    yield server

    # cleanup (stop the server) after the test
    server.stop()


@pytest.fixture(scope="session")
def session_project_dir(
    tmp_path_factory: TempPathFactory, project_dir: Path, ignore_dirs: Set[str]
) -> Path:
    """Temporary directory for the Jekyll project to be used during the session."""
    # setup session dir
    session_dir = tmp_path_factory.mktemp("session_web_src")

    # now clone from project dir
    clone_directory(project_dir, session_dir, ignore_dirs)

    return session_dir


@pytest.fixture(scope="session")
def mock_post_with_image(session_project_dir: Path) -> Tuple[Path, Path, Path]:
    """Creates a mock blog post with an associated image in the correct directories."""
    # define paths
    image_name = "test_image.jpg"
    image_path = session_project_dir / "assets/images" / image_name
    post_path = session_project_dir / "_posts/01-01-01-test-post.md"

    # ensure directories exist
    image_path.parent.mkdir(parents=True, exist_ok=True)
    post_path.parent.mkdir(parents=True, exist_ok=True)

    # write the image file
    generate_image().save(image_path, format="JPEG")

    # define the image reference
    image_reference = (
        f"![Image](/{image_path.relative_to(session_project_dir)})"
    )

    # replace the placeholder "[no image]" in the markdown file
    updated_post = generate_markdown_post().replace(
        "[No Image]", image_reference
    )

    # write the modified markdown post
    post_path.write_text(updated_post, encoding="utf-8")

    return session_project_dir, post_path, image_path


@pytest.fixture(scope="session")
def built_site(mock_post_with_image: Tuple[Path, Path, Path]) -> Path:
    """Clone project dir, build Jekyll site, reuse it for all tests."""
    # get session project dir with mocked post/image
    session_dir, *_ = mock_post_with_image

    # Run Jekyll build once
    run_jekyll_build(session_dir)

    # Return the _site directory for serving
    return session_dir / "_site"


@pytest.fixture
def built_post_path(
    mock_post_with_image: Tuple[Path, Path, Path], built_site: Path
) -> Path:
    """Returns the path to the built post HTML file in the _site directory."""
    # get session project dir and post path from the mock_post_with_image fixture
    _, post_path, _ = mock_post_with_image

    # get the filename without extension (e.g., 01-01-01-test-post)
    post_filename = post_path.stem

    # split by '-' to get the year, month, day, and title
    date_parts = post_filename.split("-")
    year, month, day = date_parts[0], date_parts[1], date_parts[2]

    # join the remaining parts as the title
    title = "-".join(date_parts[3:])

    # construct the expected path in the _site directory (Y/M/D/title format)
    built_post_path = (
        built_site / "blog" / f"20{year}/{month}/{day}/{title}.html"
    )

    return built_post_path


@pytest.fixture(scope="session")
def static_site_server(
    built_site: Path,
) -> Generator[SimpleHTTPServer, None, None]:
    """Serve the pre-built Jekyll site using a simple HTTP server."""
    # start server
    server = SimpleHTTPServer(built_site)
    server.start()

    # generate
    yield server

    # cleanup
    server.stop()


@pytest.fixture
def post_url(
    built_post_path: Path, static_site_server: SimpleHTTPServer
) -> str:
    """Returns the full URL of the built post."""
    # search for the '_site' directory in the path and extract the part below it
    try:
        site_index = built_post_path.parts.index("_site")
    except ValueError as err:
        raise ValueError(
            f"Expected '_site' directory not found in the path {built_post_path}"
        ) from err

    # get the relative path below the '_site' directory
    relative_parts = built_post_path.parts[site_index + 1 :]

    # ensure relative path includes: 'blog', year, month, day, and title
    if len(relative_parts) < 4:
        raise ValueError(f"Unexpected path structure: {relative_parts}")

    # reconstruct the URL with blog, year, month, day, and title
    blog_dir, year, month, day, *title_parts = relative_parts
    post_path = f"/{blog_dir}/{year}/{month}/{day}/{'-'.join(title_parts)}"
    post_url = urljoin(static_site_server.url(), post_path)

    return post_url


@pytest.mark.utils
def test_compare_directories(
    comp_dirs_test_data: Tuple[Path, Path], ignore_dirs: Set[str]
) -> None:
    """Test compare_directories for detecting differences."""
    # unpack dirs
    src, dst = comp_dirs_test_data

    # Sort differences to ensure consistent order
    differences = sorted(compare_directories(src, dst, ignore_dirs))

    # Sort expected differences the same way
    expected_differences = sorted(
        [
            (src / "file2.txt", dst / "file2.txt"),
            (src / "subdir" / "file3.txt", dst / "subdir" / "file3.txt"),
            (src / "file4.txt", dst / "file4.txt"),
            (src / "subdir", dst / "subdir"),
        ]
    )

    # check if sorted differences match
    assert len(differences) == len(expected_differences), (
        f"Expected {len(expected_differences)} differences, but got "
        f"{len(differences)}. Differences: {differences}"
    )

    # check each
    for expected, actual in zip(expected_differences, differences, strict=True):
        assert expected == actual, f"Expected {expected} but got {actual}"


@pytest.mark.utils
def test_generate_image_determinism() -> None:
    """Make sure image generating util is detrministic."""
    # generate identical deterministic images
    img1 = generate_image(seed=42)
    img2 = generate_image(seed=42)

    # check identical
    assert list(img1.getdata()) == list(
        img2.getdata()
    ), "Images with the same seed should be identical."


@pytest.mark.fixture
def test_clone_directory(
    temp_project_dir: Path, project_dir: Path, ignore_dirs: Set[str]
) -> None:
    """Test if the project source directory is cloned correctly."""
    # collect all differences between the project directory and temp directory
    differences = compare_directories(
        project_dir, temp_project_dir, ignore_dirs
    )

    # no differences should be found in the tracked files
    assert not differences, f"Differences found: {differences}"

    # ensure ignored directories are indeed missing in the cloned directory
    for ignored in ignore_dirs:
        assert not (
            temp_project_dir / ignored
        ).exists(), f"Ignored directory {ignored} was copied!"


@pytest.mark.fixture
def test_mock_post_with_image(
    mock_post_with_image: Tuple[Path, Path, Path]
) -> None:
    """Ensures that the post and image are created in the correct directories."""
    # get post/image paths
    _, post_path, image_path = mock_post_with_image

    # check they exist
    assert image_path.exists(), "Image file was not created!"
    assert post_path.exists(), "Markdown post was not created!"

    # get content
    content = post_path.read_text()

    # make sure content looks right
    assert (
        "![Image](/assets/images/test_image.jpg)" in content
    ), "Markdown file does not reference the image correctly!"
    assert (
        "[no image]" not in content
    ), "Placeholder '[no image]' was not removed!"


@pytest.mark.fixture
def test_post_built(
    built_post_path: Path, mock_post_with_image: Tuple[Path, Path, Path]
) -> None:
    """Test if the markdown post is converted to an HTML page after Jekyll build."""
    # get image file path
    *_, image_path = mock_post_with_image

    # Check if the HTML file exists
    assert (
        built_post_path.exists()
    ), f"Expected HTML file {built_post_path} was not generated by Jekyll"

    # Optionally, you can check the contents of the HTML file
    # e.g., check if certain text is present in the generated HTML
    with open(built_post_path, "r", encoding="utf-8") as html_file:
        html_content = html_file.read()

    # Check that the content contains the title from the markdown post
    assert (
        "Test Post" in html_content
    ), "HTML content does not contain expected title"

    # Optionally, check for image inclusion in the HTML content
    assert (
        image_path.name in html_content
    ), "HTML content does not include the image"


@pytest.mark.jekyll
def test_jekyll_installed() -> None:
    """Test that Jekyll is installed and accessible."""
    try:
        # run the `jekyll --version` command to check if Jekyll is installed
        result = subprocess.run(
            ["jekyll", "--version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # check the return code, it should be 0 if successful
        assert (
            result.returncode == 0
        ), f"Jekyll command failed with return code {result.returncode}"

        # check if Jekyll is in the version output
        assert (
            "jekyll" in result.stdout.lower()
        ), "Jekyll is not installed or accessible"

    except subprocess.CalledProcessError as e:
        pytest.fail(f"Jekyll is not installed or not accessible: {e.stderr}")


@pytest.mark.jekyll
def test_jekyll_server_start_stop(jekyll_server: JekyllServer) -> None:
    """Test that the Jekyll server starts and stops correctly."""
    # Check that the process is running initially
    assert jekyll_server.process is not None
    assert jekyll_server.process.poll() is None

    # sleep
    time.sleep(0.1)

    # Check that the server process is terminated
    assert jekyll_server.process.poll() is None


@pytest.mark.jekyll
def test_jekyll_server_explicit_stop(jekyll_server: JekyllServer) -> None:
    """Test the explicit stop method of the Jekyll server."""
    # start the server
    jekyll_server.start()

    # check process running
    assert jekyll_server.process is not None
    assert jekyll_server.process.poll() is None

    # explicitly stop the server
    jekyll_server.stop()

    # check that the server process is terminated
    assert jekyll_server.process.poll() is not None


@pytest.mark.jekyll
def test_jekyll_server_initialize(
    temp_project_dir: Path, jekyll_server: JekyllServer
) -> None:
    """Test the initialization of the JekyllServer class."""
    assert jekyll_server.cwd == temp_project_dir
    assert jekyll_server.host == "127.0.0.1"
    assert jekyll_server.port == 4000
    assert jekyll_server.source is None
    assert jekyll_server.process is not None


@pytest.mark.jekyll
def test_jekyll_build(temp_project_dir: Path) -> None:
    """Test that `jekyll build` runs successfully and `_site` directory is created."""
    # run the Jekyll build function
    result = run_jekyll_build(temp_project_dir)

    # ensure the build command executed successfully
    assert result.returncode == 0, f"Jekyll build failed: {result.stderr}"

    # verify that `_site` directory was created
    _site_dir = temp_project_dir / "_site"
    assert (
        _site_dir.exists() and _site_dir.is_dir()
    ), "_site directory was not created!"


@pytest.mark.website
def test_website_is_up(static_site_server: SimpleHTTPServer) -> None:
    """Simple test to check if the website is up and accessible."""
    try:
        # send a GET request to the site
        response = requests.get(static_site_server.url())

        # confirm success
        assert response.status_code == 200

    # unaccessible
    except requests.exceptions.ConnectionError:
        pytest.fail("Failed to connect to Jekyll site.")


@pytest.mark.website
def test_homepage_title(
    sb: BaseCase, static_site_server: SimpleHTTPServer
) -> None:
    """Basic test to check if the homepage displays."""
    # load page into browser
    sb.open(static_site_server.url())

    # get title
    title = sb.get_title()
    assert (
        "error" not in title.lower()
    ), f"Page load error detected with title: {title}"


@pytest.mark.website
def test_post_accessible(post_url: str) -> None:
    """Simple test to check if test blog post is available."""
    try:
        # send a GET request to the site
        response = requests.get(post_url)

        # confirm success
        assert response.status_code == 200

    # unaccessible
    except requests.exceptions.ConnectionError:
        pytest.fail("Failed to connect to Jekyll site.")


@pytest.mark.website
def test_blog_image_loaded(
    sb: BaseCase,
    post_url: str,
) -> None:
    """Test to check if an image is loaded on the homepage."""
    # load page into browser
    sb.open(post_url)

    # try to find the image by its tag (adjust the selector as needed)
    image = sb.find_element("img")

    # check if the image exists and is not broken
    assert image is not None, "Image not found on the page."
    assert image.get_attribute("src") != "", "Image source is empty."

    # optionally, you can check if the image is not missing
    image_src = image.get_attribute("src")
    assert image_src.startswith("http") or image_src.startswith(
        "/"
    ), "Image source URL is not valid."


@pytest.mark.config
def test_config_keys_exist(jekyll_user_config: Dict[str, str]) -> None:
    """Test that the specified keys exist in the _config.yml configuration."""
    # these are required to be in the Jekyll config (or the site won't work right)
    required_keys = [
        "markdown",
        "permalink",
        "pages_dir",
        "high_res_image",
        "low_res_image",
        "default_image",
        "url",
        "contacts",
    ]

    # these are technically optional (but recommended depending on use case)
    optional_keys = ["social", "exclude"]

    # assert that each required key exists in the loaded config
    for key in required_keys:
        assert key in jekyll_user_config, f"Missing required key: {key}"

    # check for optional keys and issue warnings if missing
    for key in optional_keys:
        if key not in jekyll_user_config:
            warnings.warn(
                f"Missing optional key: {key}", UserWarning, stacklevel=2
            )


@pytest.mark.config
def test_contacts_key_structure(jekyll_user_config: Dict[str, str]) -> None:
    """Test that the 'contacts' key exists and has the expected structure."""
    # get contacts
    contacts: Any = jekyll_user_config.get("contacts", {})

    # ensure 'contacts' is a dictionary
    assert isinstance(contacts, dict), "'contacts' should be a dictionary."


@pytest.mark.config
def test_socials_key_structure(jekyll_user_config: Dict[str, str]) -> None:
    """Test that the 'social' key exists and has the expected structure."""
    # get contacts
    social: Any = jekyll_user_config.get("social", {})

    # ensure 'contacts' is a dictionary
    assert isinstance(social, dict), "'social' should be a dictionary."


@pytest.mark.config
def test_exclude_key_structure(jekyll_user_config: Dict[str, str]) -> None:
    """Test that the 'exclude' key exists and is a list."""
    # get exclude
    exclude: Any = jekyll_user_config.get("exclude", [])

    # Ensure 'exclude' is a list
    assert isinstance(exclude, list), "'exclude' should be a list."


@pytest.mark.website
def test_contact_url_matches_config(
    sb: BaseCase,
    static_site_server: SimpleHTTPServer,
    jekyll_user_config: Dict[str, str],
) -> None:
    """Test user config contacts match the rendered site."""
    # load page into browser
    sb.open(static_site_server.url())

    # find all links on the page
    links = sb.find_elements("a")

    # Wait for the "Contact" link to be present on the page
    sb.wait_for_element("a")  # Wait for at least one link to appear on the page

    # search for the "Contact" link by its visible text
    contact_link = None
    for link in links:
        if link.text == "Contact":
            contact_link = link
            break

    # assert that the "Contact" link was found
    assert contact_link is not None, "Contact link not found!"

    # get the href attribute of the found link
    contact_url = contact_link.get_attribute("href")

    # parse the full URL to get the relative path
    parsed_url = urlparse(contact_url)
    relative_url = parsed_url.path

    # get contacts
    contacts = jekyll_user_config["contacts"]

    # confirm either of two options
    assert ("/pages/contact.html" == relative_url and len(contacts) > 1) or (
        len(contacts) == 1
    ), (
        "Expected contact URL to be '/pages/contact.html' "
        f"or a single URL from config, but got {relative_url}"
    )


@pytest.mark.website
def test_multiple_contact_links(
    sb: BaseCase,
    static_site_server: SimpleHTTPServer,
    jekyll_user_config: Dict[str, str],
) -> None:
    """Test multiple contact links in /pages/contact.html."""
    # get contact config entries
    contacts: Any = jekyll_user_config.get("contacts", {})

    # only run the test if the contacts list has more than 1 entry
    if isinstance(contacts, dict) and len(contacts) > 1:
        # notify test is executing
        print(f"Found multiple contact links: {contacts}")

        # safely join the base URL with the /pages/contacts.html path
        contacts_url = urljoin(static_site_server.url(), "/pages/contact.html")

        # load the contacts page into the browser
        sb.open(contacts_url)

        # find all links on the contacts page
        contact_links = sb.find_elements("ul.content-scroll a")

        # assert that there are multiple "Contact" links
        assert len(contact_links) > 1, (
            "Expected multiple 'Contact' links, but found "
            f"{len(contact_links)} links: {contact_links}"
        )

        # extract the contact names from the config
        contact_names = list(contacts.keys())

        # check that each contact link text matches
        for link in contact_links:
            # Check if link text matches any of the contact names
            assert any(
                name in link.text.lower() for name in contact_names
            ), f"Link text {link.text!r} does not match config contact keys."


@pytest.mark.website
def test_social_links_displayed(
    sb: BaseCase,
    static_site_server: SimpleHTTPServer,
    jekyll_user_config: Dict[str, str],
) -> None:
    """Test multiple social links in header."""
    # get social config entries
    social: Any = jekyll_user_config.get("social", {})

    # only run the test if socials are present
    if isinstance(social, dict) and len(social) > 0:
        # notify test is executing
        print(f"Found social links: {social}")

        # load the contacts page into the browser
        sb.open(static_site_server.url())

        # find social links container
        social_media_container = sb.find_element("p.social-media-links")

        # find all <a> tags within the <p> tag
        links = social_media_container.find_elements(By.TAG_NAME, "a")

        # assert that there are social media links
        assert (
            len(links) > 0
        ), f"Expected social media links but found {len(links)} links: {links}"

        # sort actual links by their <i> tag's class (fab fa-{key})
        sorted_links = sorted(
            links,
            key=lambda lnk: lnk.find_element(By.TAG_NAME, "i")
            .get_attribute("class")
            .split()[-1],
        )

        # sort expected socials by key (platform name)
        sorted_socials = sorted(social.items())

        # compare expected vs. actual values in order
        for (expected_key, expected_url), link in zip(
            sorted_socials, sorted_links, strict=True
        ):
            # get displayed icon and corresponding url from page
            actual_href = link.get_attribute("href")
            actual_icon_class = link.find_element(
                By.TAG_NAME, "i"
            ).get_attribute("class")

            # confirm urls match
            assert actual_href == expected_url, (
                f"Expected href '{expected_url!r}', "
                f"but found '{actual_href!r}' for {expected_key!r}."
            )

            # check icons match config platform name
            expected_icon_class = f"fab fa-{expected_key}"
            assert expected_icon_class in actual_icon_class, (
                f"Expected icon class '{expected_icon_class!r}', but found "
                f"'{actual_icon_class!r}'."
            )


@pytest.mark.website
def test_meta_tags(post_url: str, jekyll_user_config: Dict[str, str]) -> None:
    """Test the correct Open Graph and Twitter Card meta tags set."""
    # fetch the page content using requests
    response = requests.get(post_url)
    assert response.status_code == 200

    # get markdown post data
    expected_data = markdown_post_data()

    # get post and efault iamge updated urls
    post_updated_url = remove_html_extension(
        swap_protocol_and_domain(post_url, jekyll_user_config["url"])
    )
    default_image_url = urljoin(
        jekyll_user_config["url"], jekyll_user_config["default_image"]
    )

    # parse the HTML content
    soup = BeautifulSoup(response.text, "html.parser")

    # open graph meta tags
    og_title = soup.find("meta", property="og:title")
    og_desc = soup.find("meta", property="og:description")
    og_url = soup.find("meta", property="og:url")
    og_image = soup.find("meta", property="og:image")

    assert og_title and og_title["content"].strip() == expected_data["title"]
    assert og_desc and og_desc["content"].strip() in expected_data["content"]
    assert og_url and og_url["content"] == post_updated_url
    assert og_image and og_image["content"] == default_image_url

    # twitter card meta tags
    twt_title = soup.find("meta", attrs={"name": "twitter:title"})
    twt_desc = soup.find("meta", attrs={"name": "twitter:description"})
    twt_image = soup.find("meta", attrs={"name": "twitter:image"})

    assert twt_title and twt_title["content"].strip() == expected_data["title"]
    assert twt_desc and twt_desc["content"].strip() in expected_data["content"]
    assert twt_image and twt_image["content"] == default_image_url
