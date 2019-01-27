==================
Contribution Guide
==================

.. toctree::
   :maxdepth: 2
   :caption: Contribution Guide
   :hidden:
   :includehidden:

   Contributors <contributors>

What can I do?
--------------
Since Beiran is a free software and follows the free software
development conventions and patterns, it is open for any kind
of contribution. So you can:

- report a bug,
- make a feature request to enhance / improve Beiran,
- create a merge request if you implemented or fixed something,
- start a technical discussion,
- start a plugin project,
- join discussions on our developer email list.

The primary channel for technical issues is our issue tracker. Please
create an issue to report a bug, make a feature request or start any kind
of technical discussions. You can access Issue Dashboard by visiting
address below:

`Issue Tracker`_

You need to create an account on our GitLab_ instance. It's easy. Click
**Sign in / Register** button. Fill the registration form. Approve your
email address. That's it.

You can join our email list to follow and join design and implementation
discussions. You can ask your questions to get help. Please subscribe it
by sending an email to:

|email_list_subscribe_link|

Where is the source code?
-------------------------
Here it is: |repo_url|. Please fork it and start coding!

We accept code contributions via Merge Requests. Simply you should do:

- fork project
- change the code (on default branch or a new branch if necessary)
- click `create merge request` button
- fill the required information on the following screen
- submit your changes

and that's it.

**What information we expect** in a merge request?

- A short and descriptive title
- A detailed explanation containing
    - which issues does it fix or close (if there exist)
    - how does it solve problems
- Related labels, bug / feature / security / urgent etc.


How to code
-----------
Beiran is written in Python. We follow some general coding conventions which
is known and used widely in Python communities.

pep8
    Please follow pep8 rules. See here: https://www.python.org/dev/peps/pep-0008/

documentation
    We use sphinx to generate documentation. Do not forget inline docstrings.
    They compose the main part of our documentation. Please visit this page
    to learn how to write docstrings:
    http://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html

    Or browse the samples through current source code.

pylint
    check your code with **pylint** using our `.pylintrc` configuration
    file which can be found in root folder of project.

    All you need to do is run `pylint` and check the console output for results::

        $ pylint beiran/

        -------------------------------------------------------------------
        Your code has been rated at 10.00/10 (previous run: 8.88/10, +1.12)


requirements
    if you use a new 3rd party library, please do not forget adding
    it to `requirement.txt` files.

type hinting
    please add type hints to your objects as much as possible in
    general, it is a must for those which are supposed to be used
    by other objects or the ones in lib modules.

    please run `mypy` for type checking, there is a configuration file
    named `mypy.ini` in root folder::

        $ mypy beiran/

    The command above gives no output if there is nothing wrong.


Git Workflow
------------
Please create a topic branch using an explicit name including issue number::

    $ git checkout -b 258-build-docs-using-gitlab-ci

Change the code and commit them with a message explaining enough::

    $ git add docs/source/contribute.rst
    $ git add ..   # other changes
    $ git commit -S -m 'documentation, adds new page, how to create plugin'
    $ git push -u origin 258-build-docs-using-gitlab-ci

Sign Your Commits
-----------------
Signed commits add an extra security and trust layer to git environment.
It proves cryptographically the owner of the work.

If you haven't done already, please configure your git client to sign
your commits.

You can find detailed guide here:

https://git-scm.com/book/en/v2/Git-Tools-Signing-Your-Work

After configuring git client, add your **public key** of your gpg pair
to your gitlab profile.

See here for more details:

https://docs.gitlab.com/ce/user/project/repository/gpg_signed_commits/

.. warning:: Also please `--signoff` one of your commits to declare
 approving DCO. Please see and read carefully **Copyright** and **DCO** section below.

Copyright
---------
Along with whole Beiran source code, all your contributions are licenced
under **GPL v3** which allows anybody to copy, change, distribute or redistribute it.
By sending your source code or any kind of contributions you also accept the
licence's terms and conditions.

DCO
---
Contributors' work is protected with **Developer Certificate of Origin** which
can be found project root dir in `DCO` file or here https://developercertificate.org/

**By contributing this project you agree with `DCO` and certify your contribution as
described in `DCO`.**
