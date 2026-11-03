# Changelog

All notable changes to this project will be documented in this file. The
format is based (to a large extent) on [Keep a Changelog](https://keepachangelog.com/).

This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
The *public API* is documented in the [API Reference](https://certlib-log.readthedocs.io/page/reference/).

!!! warning

    The `certlib.log` library is currently in the _**beta**_ stage
    of development. This means, in particular, that _**backward
    incompatible**_ changes to the public API are possible (and they
    sometimes _**do happen**_) in non-major *pre-release* versions
    -- _**until**_ the final _**1.0.0**_ version is released.

***

## Release Notes

### [1.0.0-beta9] (2026-11-03)

#### Security

- **[aux]** Upgrade *development*-only dependencies in `dev/dev-requirements.txt`,
  `docs/doc-requirements.txt` and `tests/test-requirements.txt`; in particular,
  upgrade `pip` and `certifi` to versions which are unaffected by the [eMudhra
  Intermediate CA Compromise](https://emudhra.we-have-a-problem.com/) problem
  (note that the said problem is *not* specific to this library or even to Python
  environments in general; see the "Required security updates for common software"
  note in the [*General Security Notes*](#general-security-notes) section below).

- **[aux]** Furthermore, in conjunction with the above: suitably enhance
  the `dev-install.bash` helper script (and other already existing
  `dev-*.bash` scripts) as well as add two new scripts:
  `ensure-pip-v26.2.2-or-higher.bash` and
  `check-with-curl-if-immune-to-ca-compromise-2026-10.bash`. For more
  information, see the "Required security updates for common software"
  note in the [*General Security Notes*](#general-security-notes) section
  below.

- **[aux]** Implement some other security fixes/updates/enhancements --
  related to CI (GitHub *workflows*...) and/or to installing and upgrading
  *development*-only dependencies. In particular, package versions are
  now locked with cryptographic hashes also in `dev/dev-requirements.txt`
  (not only in `docs/doc-requirements.txt` and `tests/test-requirements.txt`)
  -- so that the `dev-install.bash` script is able to verify them using
  `pip` with the `--require-hashes` flag.

### [1.0.0-beta8] and earlier...

It was deemed unnecessary to provide detailed release notes for those
early versions of the library.


[Unreleased]: https://github.com/CERT-Polska/certlib-log/compare/v1.0.0-beta9...main
[1.0.0-beta9]: https://github.com/CERT-Polska/certlib-log/compare/v1.0.0-beta8...v1.0.0-beta9
[1.0.0-beta8]: https://github.com/CERT-Polska/certlib-log/compare/initial-commit...v1.0.0-beta8

***

## General Security Notes

!!! warning "Required security updates for common software"

    A global security incident, known as the [eMudhra Intermediate CA
    Compromise](https://emudhra.we-have-a-problem.com/), affects many
    kinds of software. Python environments are no exception -- most of
    them are **likely affected** [until vulnerable software is upgraded](https://discuss.python.org/t/information-for-python-users-regarding-emudhra-emsign-ca-certificate-security-incident/109576).
    In particular, all installations of **[`pip`](https://pip.pypa.io/)
    older than version 26.2.2** are typically[^1] **affected**.

    [^1]: There are some exceptions. For example, certain operating
    systems offer modified variants of `pip` that refrain from using
    any `pip`-vendored CA certificates, which makes them immune to the
    *eMudhra CA* problem (regardless of the `pip` version) -- provided
    that the system's trusted certificate store has been upgraded to an
    unaffected version. Also, CPython versions [released on 2026-10-26](https://blog.python.org/2026/10/python-3152-31410-31318-31216-31118/)
    (or later) block the use of affected certificates at the `ssl` module
    level; this protects normal uses of `pip` (regardless of its version).

    !!! warning "Implications for installation tools -- `pip` as example"

        Careless use of an affected **`pip`** version -- including
        using **`pip`** to upgrade itself -- poses the risk of injecting
        malicious software into your system.

        The same risk occurs when **`pip`** itself is patched, but the
        operating system's trusted certificate store is still affected
        (given that the default behavior of **`pip`** is -- since v24.2
        -- to use system certificates in addition to **`pip`**'s vendored
        ones).

        In both cases, the [basic countermeasure](https://pip.pypa.io/en/stable/topics/secure-installs/)
        is to force **`pip`** to *verify the SHA-256 hash* of each
        package before it is installed, while also *disallowing source
        distributions*.

    Note that **`pip`** is widely used to download and install Python
    packages, including such libraries as **`certlib.log`** (typically,
    **`pip`** is bundled with Python distributions and automatically
    included in [*virtual environments*](https://packaging.python.org/en/latest/tutorials/installing-packages/#creating-virtual-environments)).

    Furthermore, even though the **`certlib.log`** library has **no
    runtime dependencies** beyond the Python standard library, it
    does specify (like many Python projects) optional *development
    dependencies*: a set of third-party packages providing tools that
    are suggested as useful for developing the library itself. The
    **[`dev-install.bash`](https://github.com/CERT-Polska/certlib-log/blob/main/dev-install.bash)**
    helper script installs **`certlib.log`** (in "editable" mode),
    plus all those packages, into a *virtual environment*.

    **Beware: all versions of `certlib.log` older than 1.0.0-beta9**
    specify *development dependencies* that include **affected versions
    of the `pip` and `certifi` packages**.

    ***

    Fortunately, **`certlib.log` [v1.0.0-beta9](#100-beta9-2026-11-03)**
    specifies **unaffected versions** of both **`pip`** and **`certifi`**.
    To upgrade them along with the rest of your *development installation*
    of the library:

      1. Check out the **v1.0.0-beta9** (or later) [source
         code](https://github.com/CERT-Polska/certlib-log/tree/v1.0.0-beta9).
      2. Activate your **`certlib.log`**-dedicated *virtual environment*.
      3. Run the **`dev-install.bash`** script. Its hardened version will
         securely upgrade all relevant packages (in particular, **`pip`**
         and **`certifi`**).

    There is also a new script, **[`ensure-pip-v26.2.2-or-higher.bash`](https://github.com/CERT-Polska/certlib-log/blob/main/ensure-pip-v26.2.2-or-higher.bash)**,
    which securely upgrades only **`pip`** (if older than **26.2.2**).

    Both scripts require [Bash](https://www.gnu.org/software/bash/).
    Once you have executed at least one of them with no errors, in
    the context of an active *virtual environment*, you can use that
    *virtual environment*'s **`pip`** to install/upgrade any packages
    without worry -- **provided that** your operating system's trusted
    certificate store has also been suitably upgraded (here let us note
    that yet another script, **[`check-with-curl-if-immune-to-ca-compromise-2026-10.bash`](https://github.com/CERT-Polska/certlib-log/blob/main/check-with-curl-if-immune-to-ca-compromise-2026-10.bash)**,
    might help verify that -- assuming the **[`curl`](https://curl.se/)**
    tool is available and uses the system's trusted certificate store).
