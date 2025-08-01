import ast
import csv
import os
from collections import defaultdict
from datetime import datetime

import pandas as pd
from pandas import DataFrame


def to_abspath(*path_items):
  return os.path.abspath(os.path.join(*path_items))


def merge_col_headers(df: DataFrame):
  return ['__'.join([col for col in (cols_raw if type(cols_raw) == list else [cols_raw]) if len(col) > 0]) for cols_raw in df.columns]


def post_process_df(df: DataFrame, file_label: str):
  today = datetime.today().strftime('%Y%m%d-%H%M%S')

  df = df.reset_index().round(2)
  df.index.name = 'index'
  df.columns = merge_col_headers(df)
  df.to_csv(f'{file_label}_{today}.tsv', sep='\t')
  return df


def load_spr_rt_with_subj_df(excluding_low_performance, threshold):
  research_folder = '/home/pramono/work/drs/pmb-sbn-extractor/data/frank_etal'
  # Self-paced Reading df
  spr_rt_df = pd.read_csv(to_abspath(research_folder, 'selfpacedreading.RT.txt'), sep='\t')
  excluded_subjects = []
  if excluding_low_performance:
    spr_subj_df = pd.read_csv(to_abspath(research_folder, 'selfpacedreading.subj.txt'), sep='\t')
    excluded_subjects = spr_subj_df[spr_subj_df.correct < threshold].subj_nr.tolist()

  return spr_rt_df[~spr_rt_df.subj_nr.isin(excluded_subjects)][['sent_nr', 'word_pos', 'sent_pos', 'subj_nr', 'RT']]


def load_spr_rt_with_subj_by_keys(excluding_low_performance=True, threshold=.75):
  spr_df = load_spr_rt_with_subj_df(excluding_low_performance, threshold)
  spr_data = defaultdict(lambda: defaultdict(dict))
  for sent_nr, word_pos, sent_pos, subj_nr, rt in spr_df.to_numpy().tolist():
    spr_data[int(sent_nr)][int(word_pos)][int(subj_nr)] = (rt, sent_pos)
  return spr_data


def get_et_sent_nrs():
  research_folder = '/home/pramono/work/drs/pmb-sbn-extractor/data/frank_etal'
  # Eyetracking Reading df
  et_rt_df = pd.read_csv(to_abspath(research_folder, 'eyetracking.RT.txt'), sep='\t')
  return et_rt_df['sent_nr'].unique()


def load_et_with_subj_df(excluding_low_performance, threshold):
  research_folder = '/home/pramono/work/drs/pmb-sbn-extractor/data/frank_etal'
  # Eyetracking Reading df
  et_rt_df = pd.read_csv(to_abspath(research_folder, 'eyetracking.RT.txt'), sep='\t')
  excluded_subjects = []
  if excluding_low_performance:
    et_subj_df = pd.read_csv(to_abspath(research_folder, 'eyetracking.subj.txt'), sep='\t')
    excluded_subjects = et_subj_df[et_subj_df.correct < threshold].subj_nr.tolist()

  return et_rt_df[~et_rt_df.subj_nr.isin(excluded_subjects)][
    ['subj_nr', 'sent_nr', 'word_pos', 'sent_pos', 'RTfirstfix', 'RTfirstpass', 'RTrightbound', 'RTgopast']]


def load_et_rt_with_subj_by_keys(excluding_low_performance=True, threshold=.75):
  et_df = load_et_with_subj_df(excluding_low_performance, threshold)
  et_data = defaultdict(lambda: defaultdict(dict))
  for subj_nr, sent_nr, word_pos, sent_pos, rt_ff, rt_fp, rt_rb, rt_gp in et_df.to_numpy().tolist():
    et_data[int(sent_nr)][int(word_pos)][int(subj_nr)] = (rt_ff, rt_fp, rt_rb, rt_gp, sent_pos)
  return et_data


def load_indexed_anaphoras_data():
  data_folder = '/home/pramono/work/drs/pmb-sbn-extractor/data'
  with open(to_abspath(data_folder, 'indexed_aligned-anas_20250430-111141.tsv'), 'r') as raw_file:
    csv_reader = csv.DictReader(raw_file, delimiter='\t')
    loaded_data = []
    for row in csv_reader:
      row['indexed_sbn'] = ast.literal_eval(row['indexed_sbn'])
      row['indexed_manual'] = ast.literal_eval(row['indexed_manual'])
      loaded_data.append(row)
    return loaded_data


def load_indexed_manual_anaphoras():
  data_folder = '/home/pramono/work/drs/pmb-sbn-extractor/data'
  with open(to_abspath(data_folder, 'indexed-manual-anaphoras.tsv'), 'r') as raw_file:
    csv_reader = csv.DictReader(raw_file, delimiter='\t')
    return {row['sent_nr']: ast.literal_eval(row['indexed_anaphoras']) for row in csv_reader}


def load_pmb_ids():
  data_folder = '/home/pramono/work/drs/pmb-sbn-extractor/data'
  with open(to_abspath(data_folder, 'stimuli-pmb.tsv'), 'r') as raw_file:
    csv_reader = csv.DictReader(raw_file, delimiter='\t')
    return {row['pmb_id']: row['sent_nr'] for row in csv_reader}
