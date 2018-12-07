==================
Contribution Guide
==================

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

https://gitlab.com/beiran/beiran/issues

You can join our email list to follow and join design and implementation
discussions. You can ask your questions to get help. Please subscribe it
by sending an email to:

subscribe+developers@lists.beiran.io

Where is the source code?
-------------------------
Here it is: https://gitlab.com/beiran/beiran. Please fork it and start coding!

We accept code contributions via Merge Requests. It is very similar with github's
pull requests. Simply you should do:

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
    Please follow pep8 rules.

documentation
    We use sphinx to generate documentation. Do not forget inline docstrings.
    They compose the main part of our documentation. Please visit this page
    to learn how to write docstrings:
    http://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html

pylint
    check your code with **pylint** using our `.pylintrc` configuration
    file which can be found in root folder of project.

requirements
    if you use a new 3rd party library, please do not forget adding
    it to `requirement.txt` files.

type hinting
    please add type hints to your objects as much as possible in
    general, it is a must for those which are supposed to be used
    by other objects or lib like objects.

    please run `mypy` for type checking, there is a configuration file
    named `mypy.ini` in root folder.



Sign Your Commits
-----------------
Signed commits add an extra security and trust layer to git environment.
It proves cryptographically the owner of the work.

If you haven't done already, please configure your git client to sign
your commits.

You can find detailed guide here:

https://git-scm.com/book/en/v2/Git-Tools-Signing-Your-Work

After configuring git client, paste your **public key** of your gpg pair
to your gitlab profile. See here for more details:

https://docs.gitlab.com/ce/user/project/repository/gpg_signed_commits/

Copyright
---------
Along with whole Beiran source code, all your contributions are licenced
under GPL v3 which allows anybody to copy, change, distribute or redistribute it.
By sending your source code or any kind of contributions you also accept the
licence's terms and conditions.
