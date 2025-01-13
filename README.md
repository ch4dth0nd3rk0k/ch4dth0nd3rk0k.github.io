[![docker](https://github.com/DiogenesAnalytics/blog_template/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/DiogenesAnalytics/blog_template/actions/workflows/docker-publish.yml)

# Jekyll-Jupyter Blog Template
A template for building a blog, written in Jupyter Notebooks, and using Jekyll.

## Project Organization
```
├── _includes        <- Where page-specific CSS files are stored.
├── _jupyter
│   ├── notebooks    <- Jupyter notebooks for conversion are stored here.
│   └── templates    <- Where nbconvert templates are stored.
│
├── _layouts
│   ├── article.html <- Jekyll template defining articles.
│   └── default.html <- Jekyll "base" template used in all other templates.
│
├── _posts           <- Where Jekyll markdown posts are stored.
│
├── assets
│   ├── css          <- Where the "base" CSS file is stored.
│   └── images       <- Where image files are stored.
│
├── pages
│   └── blog.html    <- Jekyll template defining the blog page.
│
├── favicon          <- Where favicon files are stored.
├── .dockerignore    <- Ignore list for building Docker image.
├── .gitignore       <- Ignore list for Git repo.
├── pages            <- Where pages (i.e. non-post files) are stored.
├── _config.yml      <- The config file for Jekyll.
├── Dockerfile       <- Builds the Docker image used in the Makefile.
├── index.html       <- Jekyll template defining the home/index page.
├── Makefile         <- Makefile with commands like `make build-site`.
└── README.md        <- The top-level README for developers using this project.
```

## Configuration
Here we will discuss how to *customize* the template for your use case.

### Background Image
There are only two keys of the Jekyll `_config.yml` file that you need to consider:
```yml
high_res_image: "/assets/images/YOUR_HIGH_RES_IMAGE"
low_res_image: "/assets/images/YOUR_LOW_RES_IMAGE"
```

These two *keys* represent the *"high resolution"* and *"low resolution"* versions
of your *background image* (respectively).

### Social Links
You can enable the display of your *social media* links by adding the following to the
`_config.yml` file:
```yml
social:
  x-twitter: "https://twitter.com/yourprofile"
  instagram: "https://instagram.com/yourprofile"
  youtube: "https://youtube.com/yourprofile"
```

This will toggle **on** the display of the social media icons in the header.

## Make
Here we will document the different `make` commands defined in the `Makefile`.
All *commands* (excluding the `all` command which is simply executed by
running `make`) are executed by the following format: `make [COMMAND]`. To see
the *contents* of a command that will be executed upon invocation of the
command, simply run `make -n [COMMAND]`.

### Commands
+ `all`: (*aka*: `make`) defaults to converting all UN-converted notebooks
+ `jupyter`: launches the Jupyter notebook development Docker image
+ `execute`: execute all Jupyter notebooks (in place)
+ `convert`: convert all Jupyter notebooks (even if not changed)
+ `sync`: copy all converted files to necessary directories
+ `jekyll`: startup Docker container running Jekyll server
+ `build-site`: build Jekyll static site
+ `pause`: pause PSECS (to pause between commands)
+ `address`: get Docker container address/port
+ `containers`: launch all Docker containers
+ `commit`: git add/commit all synced files
+ `push`: git push to remote branch
+ `publish`: [ *WARNING* ] convert, sync, commit, and push all at once
+ `list-containers`: list all running containers
+ `stop-containers`: simply stops all running Docker containers
+ `restart-containers`: restart all containers
+ `unsync`: remove all synced files
+ `clear-nb`: simply clears Jupyter notebook output
+ `clear-output`: removes all converted files
+ `clear-jekyll`: removes Jekyll _site/ directory
+ `clean`: combines all clearing commands into one
+ `update-times`: update timestamps to now
+ `reset`: [ *WARNING* ] reverses all changes prior to `commit` command
