# -*- coding: utf-8 -*-
extensions = ['sphinx.ext.autodoc']
templates_path = ['_templates']
source_suffix = '.rst'
# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'rpmdeplint'
copyright = u'2016, Red Hat'
author = u'rpmdeplint contributors'

version = u'1.0'
release = u'1.0'

language = None

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = False


# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []
# Output file base name for HTML help builder.
htmlhelp_basename = 'rpmdeplintdoc'

# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('rpmdeplint',
     'rpmdeplint',
     'a tool to find errors in RPM packages in the context of their dependency graph',
     [author], 1)
]
