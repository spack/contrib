#!/bin/bash
set -eu
set -o pipefail

printf "\n----------------- Starting spack/contrib GitHub Action! -----------------\n"
printf "workdir: ${INPUT_WORKDIR}\n"
printf "authors: ${INPUT_AUTHORS}\n"
printf "samples: ${INPUT_SAMPLES}\n"
printf "verbose: ${INPUT_VERBOSE}\n"
printf "format: ${INPUT_FORMAT}\n"
printf "file: ${INPUT_FILE}\n"
printf "repo: ${INPUT_REPO}\n"
printf "topn: ${INPUT_TOPN}\n\n"

# GitHub token is required to use GitHub API
if [ -z "${GITHUB_TOKEN}" ]; then
   printf "A GITHUB_TOKEN is required to run contrib.\n"
   exit 1
fi

# Tell the user files found immediately
printf "\n\nFound files in root of repository:\n"
ls

# If the working directory is defined, change into it
if [ ! -z "${INPUT_WORKDIR}" ]; then
    printf "\n\nWorking directory set as ${INPUT_WORKDIR}\n"
    if [ ! -d "${INPUT_WORKDIR}" ]; then
        printf "Working directory does not exist.\n"
        exit 1
    fi
    cd "${INPUT_WORKDIR}"
fi

# If repository is defined, clone it to working directory
if [ ! -z "${INPUT_REPO}" ]; then
    printf "\n\nRepository for clone is set as ${INPUT_REPO}\n"
    git clone "${INPUT_REPO}"
    retval=$?
    if [ "${retval}" != "0" ]; then
        printf "Issue cloning repository.\n"
        exit 1
    fi
fi

# Show the user where we are
printf "\n\nPresent working directory is:"
pwd
ls

# Ensure the file exists
if [ ! -f "${INPUT_FILE}" ]; then
    printf "Input file ${INPUT_FILE} is not found in the working directory.\n"
    exit 1
fi

# Ensure the output format is allowed (simple grep of allowed list)
printf "pdf svg png jpg gif\n" | grep -w "${INPUT_FORMAT}"
retval=$?
if [ "${retval}" != "0" ]; then
    printf "${INPUT_FORMAT} is not supported. Choose from pdf,svg,png,jpg,gif\n"
    exit 1
fi

# Samples cannot be equal to 1 (sets division by 0 error)
if [ "${INPUT_SAMPLES}" == "1" ]; then
    printf "samples must be set to 0 (all commits) or greater than or equal to 2.\n"
    exit 1
fi

# Assemble command
COMMAND="contrib --samples ${INPUT_SAMPLES} --file ${INPUT_FILE} --format ${INPUT_FORMAT}"

# TopN Contributors to collapse into "other"
if [ ! -z "${INPUT_TOPN}" ]; then
    printf "Adding option 'topn' to collapse contributors into 'other' after ${INPUT_TOPN}\n"
    COMMAND="$COMMAND --topn ${INPUT_TOPN}"
fi

# Add verbose output
if [ ! -z "${INPUT_VERBOSE}" ]; then
    printf "Adding --verbose\n"
    COMMAND="$COMMAND --verbose"
fi

printf "$COMMAND\n"

# If there is an authors file, update the org map
if [ ! -z "${INPUT_AUTHORS}" ]; then
    contrib --update-org-map
fi

# Run contrib
$COMMAND

# Derive output file
OUTPUT=$(ls loc*.${INPUT_FORMAT})

printf "::set-output name=plot::${OUTPUT}\n"
