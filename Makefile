.PHONY: all check-docker check-image-jupyter check-image-tests check-images \
        check-workdir-tests check-deps-jupyter check-deps-tests check-all build-jupyter \
        build-tests jupyter execute convert check-renamed-images \
        check-renamed-posts check-renamed clear-renamed-images \
        clear-renamed-posts clear-renamed sync sync-check jekyll build-site \
        pause address containers check-repo-safety check-git commit push \
        publish safe-repository list-containers stop-containers \
        restart-containers unsync clear-nb clear-output clear-jekyll clean \
        update-times reset print-config lint tests pytest isort black flake8 \
        mypy install-act check-act run-act-tests shell


# Usage:
# make                      # execute and convert all Jupyter notebooks
# make check-docker         # check docker and host dependencies
# make check-image-jupyter  # check if the Jupyter Docker image exists
# make check-image-tests    # check if the Test Docker image exists
# make check-images         # check all docker images
# make check-workdir-tests  # confirm working dir is correct
# make check-deps-jupyter   # check Jupyter dependencies inside Docker
# make check-deps-tests     # check test dependencies inside Docker
# make check-all            # check all dependencies (Docker, Jupyter, Tests)
# make build-jupyter        # build jupyter Docker image
# make build-tests          # build test docker image
# make jupyter              # startup docker container running jupyter server
# make execute              # execute all jupyter notebooks (in place)
# make convert              # convert all jupyter notebooks (include unchanged)
# make check-renamed-images # check for lingering images
# make check-renamed-posts  # check for untracked posts
# make check-renamed        # check for all renamed posts/images
# make clear-renamed-images # clear lingering images
# make clear-renamed-posts  # clear renamed posts and their image dirs
# make clear-renamed        # clear all renamed posts/images
# make sync                 # copy all converted files to necessary directories
# make sync-check           # sync and check converted and blogging dirs
# make jekyll               # startup docker container running jekyll server
# make build-site           # build jekyll static site
# make pause                # pause PSECS (to pause between commands)
# make address              # get docker container address/port
# make containers           # launch all docker containers
# make check-safedir        # check if safe dir is setup
# make check-git            # check if git is installed
# make commit               # git add/commit all synced files
# make push                 # git push to remote branch
# make publish              # WARNING: convert, sync, commit, and push at once
# make safe-repository      # mark the repository as safe
# make list-containers      # list all running containers
# make stop-containers      # simply stops all running docker containers
# make restart-containers   # restart all containers
# make unsync               # remove all synced files
# make clear-nb             # simply clears jupyter notebook output
# make clear-output         # removes all converted files
# make clear-jekyll         # removes jekyll _site/ directory
# make clean                # combines all clearing commands into one
# make update-times         # update timestamps to now
# make reset                # WARNING: completely reverses all changes
# make print-config         # print info on variables used
# make lint                 # run linters
# make tests                # run full testing suite
# make pytest               # run pytest in docker container
# make isort                # run isort in docker container
# make black                # run black in docker container
# make flake8               # run flake8 in docker container
# make mypy                 # run mypy in docker container
# make install-act          # # install act command
# make check-act            # check if act is installed
# make run-act-tests        # run github action tests locally
# make shell                # create interactive shell in docker container


################################################################################
# GLOBALS                                                                      #
################################################################################

# make cli args
OFRMT := markdown
THEME := dark
TMPLT := jekyll_markdown
BASDR := _jupyter
PSTDR := _posts
OUTDR := ${BASDR}/converted
INTDR := ${BASDR}/notebooks
TMPDR := ${BASDR}/templates
DCTNR := $(notdir $(PWD))
LGLVL := WARN
FGEXT := _files
FGSDR := 'assets/images/{notebook_name}${FGEXT}'
GITBR := master
GITRM := origin
PSECS := 5

# extensions available
OEXT_html     = html
OEXT_latex    = tex
OEXT_pdf      = pdf
OEXT_webpdf   = pdf
OEXT_markdown = md
OEXT_rst      = rst
OEXT_script   = py
OEXT_notebook = ipynb
OEXT = ${OEXT_${OFRMT}}

# individual conversion flag variables
LGLFL = --log-level ${LGLVL}
OUTFL = --to ${OFRMT}
THMFL = --theme ${THEME}
TMPFL = --template ${TMPLT}
ODRFL = --output-dir ${OUTDR}
FIGDR = --NbConvertApp.output_files_dir=${FGSDR}
XTRDR = --TemplateExporter.extra_template_basedirs=${TMPDR}
RMTGS = --TagRemovePreprocessor.enabled=True
RMCEL = --TagRemovePreprocessor.remove_cell_tags remove_cell
RMNPT = --TagRemovePreprocessor.remove_input_tags remove_input
RMIPT = --TemplateExporter.exclude_input_prompt=True
RMOPT = --TemplateExporter.exclude_output_prompt=True
RMWSP = --RegexRemovePreprocessor.patterns '\s*\Z'

# check for conditional vars
ifdef NOTMPLT
  undefine TMPFL
endif
ifdef NOTHEME
  undefine THMFL
endif

# combined conversion flag variables
TMPFLGS = ${OUTFL} ${THMFL} ${TMPFL} ${ODRFL} ${FIGDR} ${XTRDR}
RMVFLGS = ${RMTGS} ${RMCEL} ${RMNPT} ${RMIPT} ${RMOPT} ${RMWSP}

# final conversion flag variable
CNVRSNFLGS = ${LGLFL} ${TMPFLGS} ${RMVFLGS}

# notebook-related variables
CURRENTDIR := $(shell pwd)
SAFEGITDIR ?= $(CURRENTDIR)
NOTEBOOKS  := $(shell find ${INTDR} -name "*.ipynb" -not -path "*/.ipynb_*/*")
OUTPUTFLS  := $(patsubst ${INTDR}/%.ipynb, ${PSTDR}/%.${OEXT}, ${NOTEBOOKS})

# extract the github username from the remote URL (SSH or HTTPS)
get_github_user = $(shell \
    remote_url=$(1); \
    if echo $$remote_url | grep -q "git@github.com"; then \
	    dirname $$remote_url | sed 's/\:/ /g' | awk '{print $$2}' | \
	    cut -d/ -f1 | tr '[:upper:]' '[:lower:]'; \
    elif echo $$remote_url | grep -q "https://github.com"; then \
	    echo $$remote_url | sed 's/https:\/\/github.com\/\([^\/]*\)\/.*/\1/' | \
	    tr '[:upper:]' '[:lower:]'; \
    else \
        echo "Invalid remote URL: $$remote_url" && exit 1; \
    fi)

# dynamically retrieve the github username, repository name, and branch
GITHUB_USER = $(call get_github_user,$(shell git config --get remote.origin.url))
REPO_NAME ?= $(shell basename -s .git `git config --get remote.origin.url`)
GIT_BRANCH ?= $(shell git rev-parse --abbrev-ref HEAD)

# docker-related variables
JKLCTNR = jekyll.${DCTNR}
JPTCTNR = jupyter.${DCTNR}
JKYLIMG = jekyll/jekyll:4.2.0
DCKRSRC = /usr/local/src/$(REPO_NAME)
DCKRTTY := $(if $(filter true,$(NOTTY)),-i,-it)
USE_VOL ?= true
USE_USR ?= true
JPTRVOL = $(if $(filter true,$(USE_VOL)),-v ${CURRENTDIR}:/home/jovyan,)
TESTVOL = $(if $(filter true,$(USE_VOL)),-v ${CURRENTDIR}:${DCKRSRC},)
DCKRUSR = $(if $(filter true,$(USE_USR)),--user $(shell id -u):$(shell id -g),)
DCKRRUN = docker run --rm ${JPTRVOL} ${DCKRTTY}
DCKRTST = docker run --rm ${DCKRUSR} ${TESTVOL} ${DCKRTTY}
DCKRTAG ?= $(GIT_BRANCH)
DCKR_PULL ?= true
DCKR_NOCACHE ?= false
DCKRIMG_BASE ?= ghcr.io/$(GITHUB_USER)/$(REPO_NAME):$(DCKRTAG)
DCKRIMG_JPYTR ?= ${DCKRIMG_BASE}_jupyter
DCKRIMG_TESTS ?= ${DCKRIMG_BASE}_testing

# Define the docker build command with optional --no-cache
define DOCKER_BUILD
	docker build --build-arg DCKRSRC=${DCKRSRC} -t $1 . --load --target $2 \
	  $(if $(filter true,$(DCKR_NOCACHE)),--no-cache)
endef

# Function to conditionally pull or build the docker image
define DOCKER_PULL_OR_BUILD
	$(if $(filter true,$(DCKR_PULL)), \
	  docker pull $1 || (echo "Pull failed. Building Docker image for $1..." && \
	  $(call DOCKER_BUILD,$1,$2)), $(call DOCKER_BUILD,$1,$2))
endef

# check for conditional vars to turn off docker
ifdef NODOCKER
  undefine DCKRRUN
  undefine DCKRTST
  undefine DCKRIMG
  undefine DCKRTAG
  undefine DCKRIMG_JPYTR
  undefine DCKRIMG_TESTS
  undefine DOCKER_BUILD
  undefine DOCKER_PULL_OR_BUILD
endif

# jupyter nbconvert vars
NBEXEC = jupyter nbconvert --to notebook --execute --inplace
NBCNVR = jupyter nbconvert ${CNVRSNFLGS}
NBCLER = jupyter nbconvert --clear-output --inplace

# get a list of untracked posts that do not have corresponding notebooks
find_untracked_posts = $(shell \
  git ls-files --others --exclude-standard _posts/*.md | \
  while read post; do \
    notebook="_jupyter/notebooks/$$(basename "$$post" .md).ipynb"; \
    if [ ! -f "$$notebook" ]; then \
      echo "$$post"; \
    fi; \
  done)

# Define the Make function
define process-renamed-images
	if [ ! -d "$(OUTDR)" ]; then \
	  echo "⚠️ Warning: $(OUTDR) directory is missing. Run 'make sync' first."; \
	  exit 1; \
	fi; \
	mode=$(1); \
	echo "$$mode renamed or lingering images..."; \
	for post in $(wildcard $(OUTDR)/*.md); do \
	  post_name=$$(basename $$post .md); \
	  image_dir="assets/images/$${post_name}$(FGEXT)"; \
	  out_image_dir="$(OUTDR)/assets/images/$${post_name}$(FGEXT)"; \
		if [ ! -d "$$out_image_dir" ]; then \
	    if [ -d "$$image_dir" ]; then \
	      if [ "$$mode" = "Clearing" ]; then \
	        echo "🗑️ Removed obsolete image directory: $$image_dir (no longer used)"; \
	        rm -rf "$$image_dir"; \
	      else \
	        echo "❌ Lingering image directory detected: $$image_dir"; \
	      fi; \
	    fi; \
	    continue; \
	  fi; \
	  if [ -d $$image_dir ]; then \
	    for img in $$image_dir/*; do \
	      if ! [ -f "$(OUTDR)/assets/images/$${post_name}$(FGEXT)/$$(basename $$img)" ]; then \
	        if [ "$$mode" = "Clearing" ]; then \
	          rm -f $$img; \
	          echo "🗑️ Removed lingering image: $$img"; \
	        else \
	          echo "❌ Lingering image detected: $$img"; \
	        fi; \
	      fi; \
	    done; \
	  fi; \
	done
endef

# testing-related variables
USE_NBQA ?= true
NBQA_NOTEBOOKS ?= $(NOTEBOOKS)
PYTHON_TARGETS := tests/
PYTHON_FILES := $(shell find $(PYTHON_TARGETS) -type f -name '*.py')

# linter command function that dynamically decides to use nbqa or not
define BUILD_LINTER_COMMAND
	@if [ ! -z "$(PYTHON_FILES)" ] && [ "$(USE_NBQA)" = "true" ] && [ ! -z "$(NBQA_NOTEBOOKS)" ]; then \
		${DCKRTST} ${DCKRIMG_TESTS} $(1) $(PYTHON_FILES); \
		${DCKRTST} ${DCKRIMG_TESTS} nbqa $(1) $(NBQA_NOTEBOOKS); \
	elif [ ! -z "$(PYTHON_FILES)" ]; then \
		${DCKRTST} ${DCKRIMG_TESTS} $(1) $(PYTHON_FILES); \
	elif [ "$(USE_NBQA)" = "true" ] && [ ! -z "$(NBQA_NOTEBOOKS)" ]; then \
		${DCKRTST} ${DCKRIMG_TESTS} nbqa $(1) $(NBQA_NOTEBOOKS); \
	fi
endef

################################################################################
# COMMANDS                                                                     #
################################################################################

# define a rule to convert Jupyter notebooks to desired output format
$(PSTDR)/%.$(OEXT): $(INTDR)/%.ipynb
	${DCKRRUN} ${DCKRIMG_JPYTR} ${NBEXEC} $<
	${DCKRRUN} ${DCKRIMG_JPYTR} ${NBCNVR} $<

# define the default target
all: $(OUTPUTFLS)

# check docker and host dependencies
check-docker:
	@ echo "Checking Docker and host dependencies..."
	@ if command -v docker >/dev/null 2>&1; then \
	  echo "✅ Docker is installed."; \
	else \
	  echo "❌ Docker is NOT installed. Please install Docker to proceed."; \
	  exit 1; \
	fi
	@ if docker --version >/dev/null 2>&1; then \
	  echo "✅ Docker is running!"; \
	else \
	  echo "❌ Docker is not running or accessible."; \
	  exit 1; \
	fi

# check if jupyter docker image exists
check-image-jupyter: check-docker
	@ if ! docker images --format "{{.Repository}}:{{.Tag}}" | \
	    grep -q "^${DCKRIMG_JPYTR}$$"; then \
	  echo "❌ Error: Docker image '${DCKRIMG_JPYTR}' is missing."; \
	  echo "Please build it using 'make build-jupyter'."; \
	  exit 1; \
	else \
	  echo "✅ Docker image '${DCKRIMG_JPYTR}' exists."; \
	fi

# check if test docker image exists
check-image-tests: check-docker
	@ if ! docker images --format "{{.Repository}}:{{.Tag}}" | \
	    grep -q "^${DCKRIMG_TESTS}$$"; then \
	  echo "❌ Error: Docker image '${DCKRIMG_TESTS}' is missing."; \
	  echo "Please build it using 'make build-tests'."; \
	  exit 1; \
	else \
	  echo "✅ Docker image '${DCKRIMG_TESTS}' exists."; \
	fi

# crouping docker image checks
check-docker-images: check-docker check-image-jupyter check-image-tests

# confirm working dir is correct
check-workdir-tests:
	@ echo "Checking if the working directory inside the container matches ${DCKRSRC}..."
	@ container_workdir=$$(docker run --rm ${DCKRIMG_TESTS} pwd); \
	if [ "$$container_workdir" = "$(DCKRSRC)" ]; then \
	  echo "✅ Working directory matches ${DCKRSRC}."; \
	else \
	  echo "❌ Working directory does NOT match ${DCKRSRC}. Current: $$container_workdir"; \
	  exit 1; \
	fi

# check jupyter dependencies inside docker
check-deps-jupyter: check-image-jupyter
	@ echo "Checking Jupyter dependencies inside Docker..."
	@ ${DCKRRUN} ${DCKRIMG_JPYTR} sh -c "\
	  command -v jupyter > /dev/null && \
	  echo '✅ Jupyter is installed!' || echo '❌ Jupyter is missing.' && \
	  python3 -m pip show nbconvert > /dev/null && \
	  echo '✅ nbconvert is installed!' || echo '❌ nbconvert is missing.'"

# check if test docker image exists
check-deps-tests: check-image-tests check-workdir-tests
	@ echo "Checking test dependencies inside Docker..."
	@ ${DCKRTST} ${DCKRIMG_TESTS} sh -c "\
	  command -v bash > /dev/null && \
	  echo '✅ bash is installed!' || echo '❌ bash is missing.' && \
	  command -v find > /dev/null && \
	  echo '✅ find is installed!' || echo '❌ find is missing.' && \
	  command -v git > /dev/null && \
	  echo '✅ git is installed!' || echo '❌ git is missing.' && \
	  command -v make > /dev/null && \
	  echo '✅ make is installed!' || echo '❌ make is missing.' && \
	  command -v rsync > /dev/null && \
	  echo '✅ rsync is installed!' || echo '❌ rsync is missing.' && \
	  command -v jupyter > /dev/null && \
	  echo '✅ jupyter is installed!' || echo '❌ jupyter is missing.' && \
	  command -v pytest > /dev/null && \
	  echo '✅ pytest is installed!' || echo '❌ pytest is missing.' && \
	  command -v isort > /dev/null && \
	  echo '✅ isort is installed!' || echo '❌ isort is missing.' && \
	  command -v flake8 > /dev/null && \
	  echo '✅ flake8 is installed!' || echo '❌ flake8 is missing.' && \
	  command -v mypy > /dev/null && \
	  echo '✅ mypy is installed!' || echo '❌ mypy is missing.' && \
	  command -v black > /dev/null && \
	  echo '✅ black is installed!' || echo '❌ black is missing.' && \
	  command -v sbase > /dev/null && \
	  echo '✅ sbase is installed!' || echo '❌ sbase is missing.' && \
	  echo '✅ All testing dependencies are present!'"

# check all dependencies
check-all: check-docker-images check-deps-jupyter check-deps-tests
	@ echo "All dependencies have been checked successfully!"

# build jupyter docker image with conditional pull and build
build-jupyter:
	@ echo "Building Jupyter Docker image..."
	@ $(call DOCKER_PULL_OR_BUILD,${DCKRIMG_JPYTR},jupyter)

# build testing docker image with conditional pull and build
build-tests:
	@ echo "Building Test Docker image..."
	@ $(call DOCKER_PULL_OR_BUILD,${DCKRIMG_TESTS},testing)

# launch jupyter notebook development docker image
jupyter:
	@ if ! docker ps --format={{.Names}} | grep -q "${JPTCTNR}"; then \
	  echo "Launching Jupyter in Docker container -> ${JPTCTNR} ..."; \
	  docker run -d \
	             --rm \
	             --name ${JPTCTNR} \
	             -e PYTHONPATH=/home/jovyan/src \
	             -e JUPYTER_ENABLE_LAB=yes \
	             -p 8888 \
	             -v "${CURRENTDIR}":/home/jovyan \
	             ${DCKRIMG_JPYTR} && \
	  if ! grep -sq "${JPTCTNR}" "${CURRENTDIR}/.running_containers"; then \
	    echo "${JPTCTNR}" >> .running_containers; \
	  fi \
	else \
	  echo "Container already running: ${JPTCTNR}. Try setting DCTNR manually."; \
	fi

# execute all notebooks and store output inplace
execute:
	@ echo "Executing all Jupyter notebooks: ${NOTEBOOKS}"
	@ ${DCKRRUN} ${DCKRIMG_JPYTR} ${NBEXEC} ${NOTEBOOKS}

# convert all notebooks to HTML
convert:
	@ echo "Converting all Jupyter notebooks: ${NOTEBOOKS}"
	@ ${DCKRRUN} ${DCKRIMG_JPYTR} ${NBCNVR} ${NOTEBOOKS}

# check for lingering images
check-renamed-images:
	@ $(call process-renamed-images,Checking)

# check for untracked posts
check-renamed-posts:
	@ echo "Checking for untracked posts with no corresponding notebooks..."
	@ untracked_posts="$(find_untracked_posts)"; \
	if [ -n "$$untracked_posts" ]; then \
	  echo "⚠️ Untracked posts found:"; \
	  echo "$$untracked_posts"; \
	  echo "Suggested cleanup: make clear-renamed"; \
	else \
	  echo "✅ No untracked posts found."; \
	fi

# check for all renamed
check-renamed: check-renamed-posts check-renamed-images

# clear lingering images
clear-renamed-images:
	@ $(call process-renamed-images,Clearing)

# clear renamed posts and their corresponding image dirs
clear-renamed-posts:
	@ echo "Cleaning up untracked posts and their image directories..."; \
	untracked_posts="$(find_untracked_posts)"; \
	if [ -n "$$untracked_posts" ]; then \
	  for post in $$untracked_posts; do \
	    rm -f "$$post"; \
	    echo "🗑️ Removed untracked post: $$post"; \
	    # extract the base name (without extension) of the post \
	    notebook_name=$$(basename $$post .md); \
	    # remove the corresponding image directory from assets/images/ \
	    image_dir="assets/images/$$notebook_name"_files; \
	    if [ -d "$$image_dir" ]; then \
	      rm -rf "$$image_dir"; \
	      echo "🗑️ Removed corresponding image directory: $$image_dir"; \
	    fi; \
	  done; \
	  echo "Cleanup complete."; \
	else \
	  echo "✅ No untracked posts to remove."; \
	fi

# clear all renamed posts/images
clear-renamed: clear-renamed-posts clear-renamed-images

# sync all converted files to necessary locations in TEssay source
sync:
	@ if ls ${OUTDR} | grep -q ".*\.${OEXT}$$"; then \
	  echo "Moving all jupyter ${OFRMT} files to _posts/:"; \
	  rsync -havP ${OUTDR}/*.${OEXT} ${CURRENTDIR}/_posts/; \
	fi
	@ if [ -d "${OUTDR}/assets" ]; then \
	  echo "Moving all jupyter image files to /assets/images"; \
	  rsync -havP ${OUTDR}/assets/ ${CURRENTDIR}/assets; \
	fi

# sync and check converted and blogging dirs
sync-check: sync check-renamed

# launch jekyll local server docker image
jekyll:
	@ if ! docker ps --format={{.Names}} | grep -q "${JKLCTNR}"; then \
	  echo "Launching Jekyll in Docker container -> ${JKLCTNR} ..."; \
	  docker run -d \
	             --rm \
	             --name ${JKLCTNR} \
	             -v ${CURRENTDIR}:/srv/jekyll:Z \
	             -p 4000 \
	             ${JKYLIMG} \
	               jekyll serve && \
	  if ! grep -sq "${JKLCTNR}" "${CURRENTDIR}/.running_containers"; then \
	    echo "${JKLCTNR}" >> .running_containers; \
	  fi \
	else \
	  echo "Container already running: ${JKLCTNR}. Try setting DCTNR manually."; \
	fi

# build jekyll static site
build-site:
	@ echo "Building Jekyll static site ..."
	@ docker run -it \
	           --rm \
	           -v ${CURRENTDIR}:/srv/jekyll:Z \
	           -p 4000 \
	           ${JKYLIMG} \
	             jekyll build && \
	echo "Site successfully built!"

# simply wait for a certain amount of time
pause:
	@ echo "Sleeping ${PSECS} seconds ..."
	@ sleep ${PSECS}

# get containerized server address
address:
	@ if [ -f "${CURRENTDIR}/.running_containers" ]; then \
	while read container; do \
	  if echo "$${container}" | grep -q "${JPTCTNR}"; then \
	    echo "Jupyter server address: $$(docker logs $${container} 2>&1 | \
	          grep http://127.0.0.1 | tail -n 1 | \
	          sed s/:8888/:$$(docker port $${container} | \
	          grep '0.0.0.0:' | awk '{print $$3}' | sed 's/0.0.0.0://g')/g | \
	          tr -d '[:blank:]')"; \
	  elif echo "$${container}" | grep -q "${JKLCTNR}"; then \
	    echo "Jekyll server address: http://0.0.0.0:$$(docker port ${JKLCTNR} | \
	          grep '0.0.0.0:' | awk '{print $$3'} | sed 's/0.0.0.0://g')"; \
	  else \
	    echo "Could not find running container: $${container}." \
	         "Try running: make list-containers"; \
	  fi \
	done < "${CURRENTDIR}/.running_containers"; \
	else \
	  echo ".running_containers file not found. Is a Docker container running?"; \
	fi

# launch all docker containers
containers: jupyter jekyll pause address

# check if safe dir is setup
check-repo-safety: check-git
	@ git config --global --get-all safe.directory | grep -q "$(SAFEGITDIR)" \
	  && echo "✅ Repository is already marked safe." \
	  || echo "⚠️ Repository is NOT marked safe. Run 'make safe-repository'."

# check if git is installed
check-git:
	@ if command -v git >/dev/null 2>&1; then \
	  echo "✅ Git is installed."; \
	else \
	  echo "❌ Git is NOT installed. Please install Git to proceed."; \
	  exit 1; \
	fi

# git add and git commit synced files
commit: check-git
	@ echo "Adding and committing recently synced files to Git repository ..."
	@ while read item; do \
	  git add $$item; \
	done < ${BASDR}/.synced_history
	@ git commit -m "Adding new ${OFRMT} posts to repository."

# git push branch to remote
push: check-git
	@ echo "Pushing Git commits to remote ${GITRM} on branch ${GITBR} ..."
	@ git push ${GITRM} ${GITBR}

# super command to convert, sync, commit, and push new jupyter posts
publish: all check-git sync commit push

# command to mark the repository as safe
safe-repository: check-git
	@ echo "Marking the repository as a safe directory: $(SAFEGITDIR)"
	@ git config --global --add safe.directory $(SAFEGITDIR)

# list all running containers
list-containers:
	@ if [ -f "${CURRENTDIR}/.running_containers" ]; then \
	echo "Currently running containers:"; \
	while read container; do \
	  echo "-->  $${container}"; \
	done < "${CURRENTDIR}/.running_containers"; \
	else \
	  echo ".running_containers file not found. Is a Docker container running?"; \
	fi

# stop all containers
stop-containers:
	@ if [ -f ${CURRENTDIR}/.running_containers ]; then \
	  echo "Stopping Docker containers ..."; \
	  while read container; do \
	    echo "Container $$(docker stop $$container) stopped."; \
	  done < ${CURRENTDIR}/.running_containers; \
	  rm -f ${CURRENTDIR}/.running_containers; \
	else \
	  echo "${CURRENTDIR}/.running_containers file not found."; \
	fi

# restart all containers
restart-containers: stop-containers containers

# unsync all converted files back to original locations
unsync:
	@ echo "Removing all jupyter converted files from _posts/ and assets/ dirs:"
	@ untracked_files="$$(git ls-files --others --exclude-standard)"; \
	posts=$$(echo "$${untracked_files}" | grep "_posts" | grep ".md"); \
	assets=$$(echo "$${untracked_files}" | grep "assets/images" | \
	          grep ".png"); \
	all_files=$$(printf "$${posts}\n$${assets}"); \
	for file in $$all_files; do \
	  if echo "$$file" | grep -q ".*\.${OEXT}$$"; then \
	    rm -f "$${file}"; \
	    echo "Removed -> $$file"; \
	  else \
	    rm -rf "$${file}"; \
	    echo "Removed -> $$file"; \
	  fi \
	done; \
	echo "Unsyncing complete."

# remove output from executed notebooks
clear-nb:
	@ echo "Clearing Jupyter notebook outputs for modified and untracked files..."
	@ modified_files="$$(git diff --name-only HEAD)"; \
	untracked_files="$$(git ls-files --others --exclude-standard)"; \
	all_files=$$(printf "$${modified_files}\n$${untracked_files}" | \
	             grep '\.ipynb$$'); \
	for file in $$all_files; do \
	    echo "Clearing output for $$file"; \
	    ${DCKRRUN} ${DCKRIMG_JPYTR} ${NBCLER} "$$file"; \
	done; \
	echo "Clearing complete."

# delete all converted files
clear-output:
	@ echo "Deleting all converted files."
	@ if [ -d "${CURRENTDIR}/${OUTDR}" ]; then \
	  rm -rf "${CURRENTDIR}/${OUTDR}"; \
	fi

# clean up jekyll _site/ dir
clear-jekyll:
	@ echo "Removing Jekyll static site directory."
	@ rm -rf ${CURRENTDIR}/_site

# cleanup everything
clean: clear-output clear-nb clear-jekyll

# update timestamps to now
update-times:
	touch _posts/*.${OEXT}

# reset to original state undoing all changes
reset: unsync clean

# print info on variables used
print-config:
	@ echo "GitHub User: $(GITHUB_USER)"
	@ echo "Repository Name: $(REPO_NAME)"
	@ echo "Git Branch: $(GIT_BRANCH)"
	@ echo "Docker Source Path: $(DCKRSRC)"
	@ echo "Docker Jupyter Image: $(DCKRIMG_JPYTR)"
	@ echo "Docker Testing Image: $(DCKRIMG_TESTS)"
	@ echo "Docker Tag: $(DCKRTAG)"
	@ echo "Current Directory: $(CURRENTDIR)"
	@ echo "Jupyter Docker Container: $(JPTCTNR)"
	@ echo "Jekyll Docker Container: $(JKLCTNR)"
	@ echo "Output Directory: $(OUTDR)"
	@ echo "Sync Directory: ${BASDR}/converted"
	@ echo "Pause Time (PSECS): $(PSECS)"

# run linters
lint: isort black flake8 mypy

# run full testing suite
tests: pytest lint

# run pytest in docker container
pytest:
	@ ${DCKRTST} ${DCKRIMG_TESTS} pytest

# isort - Handle both Python and Notebooks
isort:
	@ $(call BUILD_LINTER_COMMAND,isort)

# black - Handle both Python and Notebooks
black:
	@ $(call BUILD_LINTER_COMMAND,black --line-length 80)

# flake8 - Handle both Python and Notebooks
flake8:
	@ $(call BUILD_LINTER_COMMAND,flake8 --config=tests/.flake8)

# mypy - Handle both Python and Notebooks
mypy:
	@ $(call BUILD_LINTER_COMMAND,mypy --strict --warn-unreachable --pretty \
	--show-column-numbers --show-error-context --ignore-missing-imports)

# install act command
install-act:
	@ echo "Installing act..."
	@ curl --proto '=https' --tlsv1.2 -sSf \
	  "https://raw.githubusercontent.com/nektos/act/master/install.sh" | \
	  sudo bash -s -- -b ./bin && \
	sudo mv ./bin/act /usr/local/bin/
	@ echo "act installed and moved to /usr/local/bin"

# check if act is installed
check-act:
	@ command -v act >/dev/null 2>&1 && \
	{ echo "✅ 'act' is installed!"; } || \
	{ echo "❌ Command 'act' is not installed. Please install it with: "\
	"'make install-act' 💻🔧"; exit 1; }

# run github action tests locally
run-act-tests: check-act
	@ echo "Running GitHub Action Tests locally..."
	act -j run-tests $(ARGS)

# Command to test with a custom remote URL passed as an argument
test-github-user:
	@ echo "$(call get_github_user,$(REMOTE_URL))"

# create interactive shell in docker container
shell:
	@ ${DCKRTST} ${DCKRIMG_TESTS} bash || true
