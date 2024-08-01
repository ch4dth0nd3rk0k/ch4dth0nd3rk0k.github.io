.PHONY: all jupyter execute convert sync jekyll build-site pause address \
        containers commit push publish list-containers stop-containers \
        restart-containers unsync clear-nb clear-output clear-jekyll clean \
				update-times reset

# Usage:
# make                    # execute and convert all Jupyter notebooks
# make jupyter            # startup Docker container running Jupyter server
# make execute            # execute all Jupyter notebooks (in place)
# make convert            # convert all Jupyter notebooks (even if not changed)
# make sync               # copy all converted files to necessary directories
# make jekyll             # startup Docker container running Jekyll server
# make build-site         # build jekyll static site
# make pause              # pause PSECS (to pause between commands)
# make address            # get Docker container address/port
# make containers         # launch all Docker containers
# make commit             # git add/commit all synced files
# make push               # git push to remote branch
# make publish            # WARNING: convert, sync, commit, and push all at once
# make list-containers    # list all running containers
# make stop-containers    # simply stops all running Docker containers
# make restart-containers # restart all containers
# make unsync             # remove all synced files
# make clear-nb           # simply clears Jupyter notebook output
# make clear-output       # removes all converted files
# make clear-jekyll       # removes Jekyll _site/ directory
# make clean              # combines all clearing commands into one
# make update-times       # update timestamps to now
# make reset              # WARNING: completely reverses all changes

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
CURRENTDIR := $(PWD)
NOTEBOOKS  := $(shell find ${INTDR} -name "*.ipynb" -not -path "*/.ipynb_*/*")
OUTPUTFLS  := $(patsubst ${INTDR}/%.ipynb, ${PSTDR}/%.${OEXT}, ${NOTEBOOKS})

# docker-related variables
JKLCTNR = jekyll.${DCTNR}
JPTCTNR = jupyter.${DCTNR}
JKYLIMG = jekyll/jekyll:4.2.0
DCKRIMG = ghcr.io/ch4dth0nd3rk0k/ch4dth0nd3rk0k.github.io:master
DCKRRUN = docker run --rm -v ${CURRENTDIR}:/home/jovyan -it ${DCKRIMG}
DCKRBLD = docker build -t ${DCKRIMG} . --load

# check for conditional vars to turn off docker
ifdef NODOCKER
  undefine DCKRRUN
endif

# jupyter nbconvert vars
NBEXEC = jupyter nbconvert --to notebook --execute --inplace
NBCNVR = jupyter nbconvert ${CNVRSNFLGS}
NBCLER = jupyter nbconvert --clear-output --inplace

################################################################################
# COMMANDS                                                                     #
################################################################################

# define a rule to convert Jupyter notebooks to desired output format
$(PSTDR)/%.$(OEXT): $(INTDR)/%.ipynb
	${DCKRRUN} ${NBEXEC} $<
	${DCKRRUN} ${NBCNVR} $<

# define the default target
all: $(OUTPUTFLS)

# build jupyter docker image
build-jupyter:
	${DCKRBLD}

# launch jupyter notebook development Docker image
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
	             ${DCKRIMG} && \
	  if ! grep -sq "${JPTCTNR}" "${CURRENTDIR}/.running_containers"; then \
	    echo "${JPTCTNR}" >> .running_containers; \
	  fi \
	else \
	  echo "Container already running: ${JPTCTNR}. Try setting DCTNR manually."; \
	fi

# execute all notebooks and store output inplace
execute:
	@ echo "Executing all Jupyter notebooks: ${NOTEBOOKS}"
	@ ${DCKRRUN} ${NBEXEC} ${NOTEBOOKS}

# convert all notebooks to HTML
convert:
	@ echo "Converting all Jupyter notebooks: ${NOTEBOOKS}"
	@ ${DCKRRUN} ${NBCNVR} ${NOTEBOOKS}

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

# launch jekyll local server Docker image
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
	           jekyll/jekyll:4.2.0 \
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

# git add and git commit synced files
commit:
	@ echo "Adding and committing recently synced files to Git repository ..."
	@ while read item; do \
	  git add $$item; \
	done < ${BASDR}/.synced_history
	@ git commit -m "Adding new ${OFRMT} posts to repository."

# git push branch to remote
push:
	@ echo "Pushing Git commits to remote ${GITRM} on branch ${GITBR} ..."
	@ git push ${GITRM} ${GITBR}

# super command to convert, sync, commit, and push new jupyter posts
publish: all sync commit push

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
	@untracked_files="$$(git ls-files --others --exclude-standard)"; \
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
	@echo "Clearing Jupyter notebook outputs for modified and untracked files..."
	@modified_files="$$(git diff --name-only HEAD)"; \
	untracked_files="$$(git ls-files --others --exclude-standard)"; \
	all_files=$$(printf "$${modified_files}\n$${untracked_files}" | \
	             grep '\.ipynb$$'); \
	for file in $$all_files; do \
	    echo "Clearing output for $$file"; \
	    ${DCKRRUN} ${NBCLER} "$$file"; \
	done; \
	echo "Clearing complete."

# delete all converted files
clear-output:
	@ echo "Deleting all converted files."
	@ if [ -d "${CURRENTDIR}/${OUTDR}" ]; then \
	  rm -rf "${CURRENTDIR}/${OUTDR}"; \
	fi

# clean up Jekyll _site/ dir
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
