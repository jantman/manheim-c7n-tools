.. _development:

===========
Development
===========

* Open a pull request for changes. TravisCI will test them.
* To cut a release, bump the version number in ``manheim_c7n_tools/version.py``, update ``CHANGES.rst``, and open a pull request for that. Once merged to master, tag the release in GitHub and TravisCI will build and deploy the package and Docker Hub will automatically build and tag the image.

.. _development.local:

Local Development and Testing
=============================

Clone this repo locally on a machine with Python 3.7. Then:

.. code-block:: shell

    virtualenv --python=python3.7 .
    source bin/activate
    pip install 'tox>=3.4.0'
    pip install -r requirements.txt
    python setup.py develop

To run tests: ``tox``

For information on how to run the actual commands locally, see :ref:`index`.

.. _development.testing_versions:

Testing PRs and New Versions
============================

Sometimes you'll want to test a PR or some code changes, such as a new c7n version or a PR against upstream c7n, without publishing a new release. There isn't a really clear official process for this, but here's what we're doing right now:

1. Make your changes in this repo as needed in a branch, commit them, push them somewhere (to origin if you have rights, or a fork otherwise).
2. Build and test the Docker image with ``tox -e docker``
3. Re-tag the resulting image for a private Docker registry (i.e. ``docker tag manheim/manheim-c7n-tools:TAG docker.artifactory.yourcompany.com/your-name/manheim-c7n-tools:TAG``) or your personal namespace on the Docker Hub (i.e. ``docker tag manheim/manheim-c7n-tools:TAG your-name/manheim-c7n-tools:TAG``). The ``TAG`` should be a ``test_GitHash_TimStamp`` string, such as ``test_d3e0910_1603719566``.
4. Run the image from that alternate location for testing.
