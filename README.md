# GLADOS_CLI
This is the command line interface version of GLADOS, allowing for more flexibility for users who desire a programmatic mode of navigating GLADOS. This tool runs using Python and requires no external libraries.

In order to use this tool, you must authenticate your GLADOS account with GitHub. This will be done automatically when the tool is run or can be done manually with the `-t` or `--token` option.

After signing in via GitHub, a new file called "token.glados" will be created. This will contain your token for accessing GLADOS in the future. It is strongly recommended that you add this file to ".gitignore".

Below are the operations you can perform (note that they are mutually exclusive unless otherwise stated).

## Upload & Run Experiments

To upload and run an experiment, use the `-z` or `--upload-zip` option:

```sh
python glados-cli.py -z <ZIP file containing your experiment>
```

In order for the upload to succeed, the ZIP file must contain the following

- a Python file with your experiment's code
- requirements.txt
- manifest.yaml

Upon running the experiment, its ID will be printed.

## Query Experiments

To search experiments, use the `-q` or `--query` option:

```sh
python glados-cli.py -q [experiment title]
```

This will display all experiments with the given title with the following information about them:

- experiment status
- tags
- number of completed trials
- total number of trials to run

Not entering a title will display all of your experiments.

## Download Experiment Results

To download experiment results, use the `d` or `--download` option:

```sh
python glados-cli.py -d <exp_id> [destination]
```

This will save the experiment results to the specified directory, or the current one if no destination is provided.