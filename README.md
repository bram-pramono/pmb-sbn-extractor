# PMB SBN Extractor

My name is Bram Pramono. I am a master student of AI at Utrecht University. This repository is a public repository to maintain the work out of my thesis. The topic of investigation lies around the use of Discourse Representation Theory (DRT) as the linguistic framework to evaluate human cognitive efforts in incremental language processing. To properly execute the investigation, the data should contain linguistic annotations based on incremental parsing. Such annotated data is available on the Parallel Meaning Bank (PMB). PMB provides the necessary tooling to mark sentences with linguistic information. Thereby, the analysis on cognitive efforts can be executed with higher precisions. As for the cognitive efforts themselves, we would need behavioural data to match the linguistic items with human's language processing. The behaviourl data for this thesis is based on Frank et al. (2013).

## Folder Structure

This repository is structured as following:
- `script` folder contains the python codes for two separate actions, namely the data `extractor` and the `analysis` scripts. In each of these folders, the scripts are numbered following the order of the scripts that provides data for the next executions.

- `data` folder contains the collections of predefined data or the products out of the scripts from the `script` folder.

- `doc` folder contains information regarding information out of PMB.

- `report` folder is a placeholder folder for all reports generated from the executed scripts from the `script` folder.

## How to use

The data for the `analysis` scripts are the results of combined information from PMB and the behavioural data. To combine these two, the PMB data needs to be cleaned up and aligned properly. In the script.sbnutils.py, you can find the functions that can be used to extract information out of PMB data.

For anaphora, it is only possible to extract unresolved anaphoras by manually marking the unresolved anaphoras with distance as `?`. As an example, see `data/manual-anaphora.tsv`.

Once the extractions have been completed, the necessary analysis can be done using linear mixed effect models. After some trials and errors, I cannot find pure python packages to run the analysis. Therefore, I created a script to generate data for R along with the script to execute the analysis (`script/analysis/1_prep-r-code.py`). Once the script has been executed on R, the data will be available for analysis. The data can then easily be extracted using `script/analysis/2_collect_report_values.py`. This will generate a tsv file that summarizes the target independent variable vs the dependent variable.