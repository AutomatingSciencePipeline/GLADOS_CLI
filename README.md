# GLADOS_CLI
This is the command line interface version of GLADOS, allowing for more flexibility for users who desire a programmatic mode of navigating GLADOS. This tool runs using Python and requires no external libraries.

In order to use this tool, you must authenticate your GLADOS account with GitHub. This will be done automatically when the tool is run or can be done manually with the `-t` or `--token` option.

After signing in via GitHub, a new file called "token.glados" will be created. This will contain your token for accessing GLADOS in the future. It is strongly recommended that you add this file to ".gitignore".

Below are the operations you can perform (note that they are mutually exclusive unless otherwise stated).

## Upload & Run Experiments

To upload and run an experiment, use the `-z` or `--upload-zip` option:
```
python glados-cli.py -z <ZIP file containing your experiment>
```

In order for the upload to succeed, the ZIP file must contain the following
 - a Python file with your experiment's code
 - requirements.txt
 - specifications.txt

Some additional fields you can provide include the following:
```
    --title - the experiment's title (otherwise will be auto-generated)
    --tags - a comma-separated list of experiment tags
```

Upon running the experiment, its ID will be printed.

## Check Experiment Status

To see a list of all of your running experiments, use the `-s` or `--status` option:
```
python glados-cli.py -s [experiment ID]
```

Providing an experiment ID will display the status of that experiment, which includes its state and the number of permutations it has completed.

## Query Experiments

To search experiments, use the `-q` or `--query` option:
```
python glados-cli.py -q [--title="Title"] [--tags="tags,for,experiment"]
```

Both the `--title` and `--tags` fields are optional. Not including both will display all experiments you have run.

Experiments will display sorted by date, and their dates and ID's will be visible.

## Download Experiment Results:

To download experiment results, use the `d` or `--download` option:
```
python glados-cli.py -d <exp_id> [destination]
```

This will save the experiment results to the specified directory, or the current one if no destination is provided.