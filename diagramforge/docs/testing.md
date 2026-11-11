# Testing

Testing is essential to ensure that the package works as expected. So far, there is only one single test implemented and the whole process requires your participation as the test cannot check the diagram in SPM.

### Table of Contents <!-- omit in toc -->
- [Run the Tests](#run-the-tests)
- [Acceptance Criteria](#acceptance-criteria)


## Run the Tests

The package is set up to run the tests using `pytest`. To run the tests, you can use the following command:

```bash
poetry run pytest/ -v
``` 

> You can do this in you IDE instead of the command line, of course.

This will run the one and only implemented test [`test_transform_saved_diagrams`](../tests/test_transform_saved_diagrams.py). The test reads out the JSON files stored in [`tests/data`](../tests/data) and checks if the transformation of the diagrams works as expected. If the transformation is successful, the test will pass. Otherwise, it will fail and you will need to investigate the issue. 

After the test has run, there will be a new folder called `TESTS_UPLOAD_TO_SPM` in the root directory of you project. This folder contains the transformed diagrams in JSON format. Please upload these diagrams to SPM and check whether they look as expected. There is no sensible way to check this via tests and you need to do this manually.

You are invited to add more JSON files of diagrams to the `tests/data` folder. The test will include all files automatically.

## Acceptance Criteria

Running the tests and looking at the results in SPM must be concluded successfully before any new changes can be accepted into the main branch. This is to ensure that the diagrams are transformed correctly and that the package works as expected. 

Ultimately, this is what I will check before merging any changes into the main branch. If the tests fail and the diagrams look funky I will not merge the changes. 

