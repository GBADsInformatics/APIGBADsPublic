#!/usr/bin/python3

import nox


@nox.session
def format(session):
    session.install("-r", "requirements/test_reqs.txt")
    session.run("black", ".")


@nox.session
def lint(session):
    session.install("-r", "requirements/test_reqs.txt")
    session.install("-r", "requirements/requirements.txt")
    session.run("flake8", "--exclude=venv,__pycache__,.nox", "--ignore=E501,W503")
    session.run("pylint", ".", "--disable=invalid-name")


@nox.session
def test(session):
    session.install("-r", "requirements/test_reqs.txt")
    session.install("-r", "requirements/requirements.txt")
    session.run("pytest", *session.posargs)
