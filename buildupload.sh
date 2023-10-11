#!/bin/bash

rm -rf dist

python -m build                                                   
#twine upload --repository-url https://test.pypi.org/legacy/ dist/*
twine upload --repository testpypi  dist/*