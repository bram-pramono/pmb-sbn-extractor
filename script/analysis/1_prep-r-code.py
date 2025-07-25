from datetime import datetime

import pandas as pd

from script.utils import to_abspath, load_indexed_manual_anaphoras

REFLEXIVES_WORDS = ['himself', 'itself', 'herself']
POSSESSIVES_WORDS = ['our', 'its', 'their', 'her', 'his']
MULTI_ANA_WORDS = ['them', 'our', 'they', 'them', 'their']
PUNCTUATIONS = [',', '.', "'"]

base_folder = "/home/pramono/work/drs/pmb-sbn-extractor"
data_folder = to_abspath(base_folder, 'data')
ana_count_ref = load_indexed_manual_anaphoras()

print_acc = []


def wrap_print(*messages):
  joined_message = ' '.join(messages) + '\n'
  print_acc.append(joined_message.replace('\n\n', '\n'))
  print(messages)


def flush_clean_wrap_print(file_path):
  with open(file_path, 'w') as out:
    out.writelines(print_acc)
  print_acc.clear()


# For more understanding between covariances and fixed effects, read https://stats.stackexchange.com/a/440075.

def clean_token(token: str):
  for punc in PUNCTUATIONS:
    token = token.split(punc)[0]
  return token.lower()


def is_reflexive(token: str):
  return clean_token(token) in REFLEXIVES_WORDS


def is_possessive(token: str):
  return clean_token(token) in POSSESSIVES_WORDS


def ana_category(token: str):
  if clean_token(token) != 'her' and is_possessive(token):
    return 'P'
  if is_reflexive(token):
    return 'R'
  return 'O'


def has_multiple_drefs(token: str):
  return clean_token(token) in MULTI_ANA_WORDS


def word_length(token: str):
  return len(token)


def prev_ana_count_in_sent(sent_nr, word_pos):
  return len([x for x in ana_count_ref[str(sent_nr)] if x[0] < word_pos - 1])


def enrich_with_ana_info(df):
  df['clean_token'] = df['token'].apply(clean_token)
  df['reflexive'] = df['token'].apply(is_reflexive)
  df['ana_category'] = df['token'].apply(ana_category)
  df['multiple_drefs'] = df['token'].apply(has_multiple_drefs)
  df['word_length'] = df['token'].apply(len)
  df['num_prev_anas'] = df.apply(lambda x: prev_ana_count_in_sent(x['sent_nr'], x['word_pos']), axis=1)


def enrich_with_role_info(df):
  df['word_length'] = df['token'].apply(len)


def enrich_with_storage_info(df):
  df['word_length'] = df['token'].apply(len)
  df['nr_total_roles'] = df['nr_neg_roles'] + df['nr_pos_roles']


def save_for_R(df, name):
  df.to_csv(to_abspath(data_folder, 'R_prepared', f'R_{name}.tsv'), sep='\t')


def write_r(df_name, dep_var, fixed_effects, covariates, third_cross_intercept):
  wrap_print(f'''
{df_name}<- readr::read_tsv(url("file://{data_folder}/R_prepared/R_{df_name}.tsv"))

res<-lmer({dep_var} ~ {fixed_effects} + {covariates} + (1 |subj_nr) + (1 | sent_nr), data = {df_name})

sink("{base_folder}/result/r-analysis/{df_name.replace("_df", "")}_sentnr.txt")
summary(res)
sink()
  ''')

  if third_cross_intercept is not None:
    wrap_print(f'''
res<-lmer({dep_var} ~ {fixed_effects} + {covariates} + (1 |subj_nr) + (1 | {third_cross_intercept}), data = {df_name})

sink("{base_folder}/result/r-analysis/{df_name.replace("_df", "")}_{third_cross_intercept.replace("clean_", "")}.txt")
summary(res)
sink()
    ''')


def write_r_for_ana(df_name, dep_var, fixed_effects):
  write_r(df_name, dep_var, fixed_effects, 'C(multiple_drefs) + word_length + num_prev_anas', 'clean_token')


def write_r_for_role(df_name, dep_var, fixed_effects, third_cross_intercept):
  write_r(df_name, dep_var, fixed_effects, 'word_length', third_cross_intercept)


def write_r_for_storage(df_name, dep_var, fixed_effects):
  write_r(df_name, dep_var, fixed_effects, 'word_length', None)


wrap_print('########################')
wrap_print('# DATASET CONFIGS')
wrap_print('########################')
skip_first_last_for_ana = True

wrap_print('library(readr)')
wrap_print('library(lme4)')
wrap_print('library(lmerTest)')

wrap_print('########################')
wrap_print('# MANUAL ANAPHORAS')
wrap_print('########################')

wrap_print('########################')
wrap_print('# FOR SPR ANAPHORAS')
wrap_print('########################')

# Load MANUAL data
ori_manual_spr_ana_df = pd.read_csv(to_abspath(data_folder, 'manual_ana_spr_per_subj_rts.tsv'), sep='\t')
if skip_first_last_for_ana:
  ori_manual_spr_ana_df['last_word'] = ori_manual_spr_ana_df.token.str.endswith('.')
  ori_manual_spr_ana_df.last_word = ori_manual_spr_ana_df.last_word.astype(int)

# clean up data
manual_spr_ana_df = ori_manual_spr_ana_df.drop(ori_manual_spr_ana_df[ori_manual_spr_ana_df.distance.str.contains('\+')].index)
enrich_with_ana_info(manual_spr_ana_df)

if skip_first_last_for_ana:
  # Exclude first and last word
  manual_spr_ana_df = manual_spr_ana_df.drop(manual_spr_ana_df[manual_spr_ana_df.word_pos == 1].index)
  manual_spr_ana_df = manual_spr_ana_df.drop(manual_spr_ana_df[manual_spr_ana_df.last_word == 1].index)

manual_spr_ana_df['resolved'] = manual_spr_ana_df.distance != '?'
manual_spr_ana_df.resolved = manual_spr_ana_df.resolved.astype(int)

wrap_print('## RT ~ resolved')

df_name = 'manual_ana_spr_rt_resolved_df'
save_for_R(manual_spr_ana_df, df_name)
write_r_for_ana(df_name, 'log(rt)', 'C(resolved) * sent_pos * C(reflexive) * word_pos')

df_name = 'manual_ana_spr_spill_resolved_df'
spill_manual_spr_ana_df = manual_spr_ana_df[manual_spr_ana_df.spill > 0]
save_for_R(spill_manual_spr_ana_df, df_name)
write_r_for_ana(df_name, 'log(spill)', 'C(resolved) * sent_pos * C(reflexive) * word_pos')

wrap_print('## RT ~ distance')

manual_spr_ana_distance_df = manual_spr_ana_df[manual_spr_ana_df.distance != '?']
manual_spr_ana_distance_df.distance = manual_spr_ana_distance_df.distance.astype(int)

df_name = 'manual_ana_spr_rt_distance_df'
save_for_R(manual_spr_ana_distance_df, df_name)
write_r_for_ana(df_name, 'log(rt)', 'distance * C(reflexive) * word_pos')

spill_manual_spr_ana_distance_df = manual_spr_ana_distance_df[manual_spr_ana_distance_df.spill > 0]

df_name = 'manual_ana_spr_spill_distance_df'
save_for_R(spill_manual_spr_ana_distance_df, df_name)
write_r_for_ana(df_name, 'log(spill)', 'distance * C(reflexive) * word_pos')

wrap_print('########################')
wrap_print('# FOR ET ANAPHORAS')
wrap_print('########################')

# Load MANUAL data
ori_manual_et_ana_df = pd.read_csv(to_abspath(data_folder, 'manual_ana_et_per_subj_rts.tsv'), sep='\t')
if skip_first_last_for_ana:
  ori_manual_et_ana_df['last_word'] = ori_manual_et_ana_df.token.str.endswith('.')
  ori_manual_et_ana_df.last_word = ori_manual_et_ana_df.last_word.astype(int)


# clean up data
manual_et_ana_df = ori_manual_et_ana_df.drop(ori_manual_et_ana_df[ori_manual_et_ana_df.distance.str.contains('\+')].index)
enrich_with_ana_info(manual_et_ana_df)

if skip_first_last_for_ana:
  # Exclude first and last word
  manual_et_ana_df = manual_et_ana_df.drop(manual_et_ana_df[manual_et_ana_df.word_pos == 1].index)
  manual_et_ana_df = manual_et_ana_df.drop(manual_et_ana_df[manual_et_ana_df.last_word == 1].index)

manual_et_ana_df['resolved'] = manual_et_ana_df.distance != '?'
manual_et_ana_df.resolved = manual_et_ana_df.resolved.astype(int)

wrap_print('## skip ~ resolved')

manual_et_ana_df['target_skipped'] = manual_et_ana_df['rt_fp'] == 0
manual_et_ana_df.target_skipped = manual_et_ana_df.target_skipped.astype(int)

skip_rate_fixed_effects = 'C(resolved) * sent_pos * C(reflexive) * word_pos'

df_name = 'manual_ana_et_rt_skipped_resolved_df'
save_for_R(manual_et_ana_df, df_name)
write_r_for_ana(df_name, 'target_skipped', skip_rate_fixed_effects)

spill_manual_et_ana_df = manual_et_ana_df[manual_et_ana_df.spill_fp >= 0]
spill_manual_et_ana_df['spill_skipped'] = spill_manual_et_ana_df['spill_fp'] == 0
spill_manual_et_ana_df.spill_skipped = spill_manual_et_ana_df.spill_skipped.astype(int)

df_name = 'manual_ana_et_spill_skipped_resolved_df'
save_for_R(spill_manual_et_ana_df, df_name)
write_r_for_ana(df_name, 'spill_skipped', skip_rate_fixed_effects)

wrap_print('## (non_reflexive) skip ~ resolved')

non_reflexive_manual_et_ana_df = manual_et_ana_df.drop(manual_et_ana_df[manual_et_ana_df.reflexive == 'TRUE'].index)
skip_rate_fixed_effects = 'C(resolved) * sent_pos * word_pos'

df_name = 'manual_ana_et_rt_skipped_resolved_non_reflexive_df'
save_for_R(non_reflexive_manual_et_ana_df, df_name)
write_r_for_ana(df_name, 'target_skipped', skip_rate_fixed_effects)

non_reflexive_spill_manual_et_ana_df = spill_manual_et_ana_df.drop(spill_manual_et_ana_df[spill_manual_et_ana_df.reflexive == 'TRUE'].index)

df_name = 'manual_ana_et_spill_skipped_resolved_non_reflexive_df'
save_for_R(non_reflexive_spill_manual_et_ana_df, df_name)
write_r_for_ana(df_name, 'spill_skipped', skip_rate_fixed_effects)

wrap_print('## skip ~ distance')

manual_et_ana_distance_df = manual_et_ana_df[manual_et_ana_df.distance != '?']
manual_et_ana_distance_df.distance = manual_et_ana_distance_df.distance.astype(int)

df_name = 'manual_ana_et_rt_skipped_distance_df'
save_for_R(manual_et_ana_distance_df, df_name)
write_r_for_ana(df_name, 'target_skipped', 'distance * C(reflexive) * word_pos')

spill_manual_et_ana_distance_df = spill_manual_et_ana_df[spill_manual_et_ana_df.distance != '?']

df_name = 'manual_ana_et_spill_skipped_distance_df'
save_for_R(spill_manual_et_ana_distance_df, df_name)
write_r_for_ana(df_name, 'spill_skipped', 'distance * C(reflexive) * word_pos')

wrap_print('## RT ~ resolved')

non_skipped_rt_manual_et_ana_df = manual_et_ana_df[manual_et_ana_df.rt_fp > 0]

df_name = 'manual_ana_et_rt_resolved_df'
save_for_R(non_skipped_rt_manual_et_ana_df, df_name)
write_r_for_ana(df_name, 'log(rt_fp)', 'C(resolved) * sent_pos * C(reflexive) * word_pos')

non_skipped_spill_manual_et_ana_df = manual_et_ana_df[manual_et_ana_df.spill_fp > 0]

df_name = 'manual_ana_et_spill_resolved_df'
save_for_R(non_skipped_spill_manual_et_ana_df, df_name)
write_r_for_ana(df_name, 'log(spill_fp)', 'C(resolved) * sent_pos * C(reflexive) * word_pos')

wrap_print('## RT ~ distance')

manual_et_ana_distance_df = manual_et_ana_df[manual_et_ana_df.distance != '?']
non_skipped_rt_manual_et_ana_distance_df = manual_et_ana_distance_df[manual_et_ana_distance_df.rt_fp > 0]

df_name = 'manual_ana_et_rt_distance_df'
save_for_R(non_skipped_rt_manual_et_ana_distance_df, df_name)
write_r_for_ana(df_name, 'log(rt_fp)', 'distance * C(reflexive) * word_pos')

non_skipped_spill_manual_et_ana_distance_df = manual_et_ana_distance_df[manual_et_ana_distance_df.spill_fp > 0]

df_name = 'manual_ana_et_spill_distance_df'
save_for_R(non_skipped_spill_manual_et_ana_distance_df, df_name)
write_r_for_ana(df_name, 'log(spill_fp)', 'distance * C(reflexive) * word_pos')


wrap_print('########################')
wrap_print('# SBN ANAPHORAS')
wrap_print('########################')

wrap_print('########################')
wrap_print('# FOR SPR ANAPHORAS')
wrap_print('########################')

# Load SBN data
ori_manual_spr_ana_df = pd.read_csv(to_abspath(data_folder, 'manual_ana_spr_per_subj_rts.tsv'), sep='\t')
if skip_first_last_for_ana:
  ori_manual_spr_ana_df['last_word'] = ori_manual_spr_ana_df.token.str.endswith('.')
  ori_manual_spr_ana_df.last_word = ori_manual_spr_ana_df.last_word.astype(int)
unresolved_spr_ana_df = ori_manual_spr_ana_df[ori_manual_spr_ana_df.distance == '?']

ori_sbn_spr_ana_df = pd.read_csv(to_abspath(data_folder, 'sbn_ana_spr_per_subj_rts.tsv'), sep='\t')
# clean up data
sbn_spr_ana_df = ori_sbn_spr_ana_df.drop(ori_sbn_spr_ana_df[ori_sbn_spr_ana_df.distance > 0].index)
enrich_with_ana_info(sbn_spr_ana_df)

if skip_first_last_for_ana:
  # Exclude first and last word
  sbn_spr_ana_df = sbn_spr_ana_df.drop(sbn_spr_ana_df[sbn_spr_ana_df.word_pos == 1].index)
  sbn_spr_ana_df = sbn_spr_ana_df.drop(sbn_spr_ana_df[sbn_spr_ana_df.last_word == 1].index)
  unresolved_spr_ana_df = unresolved_spr_ana_df.drop(unresolved_spr_ana_df[unresolved_spr_ana_df.word_pos == 1].index)
  unresolved_spr_ana_df = unresolved_spr_ana_df.drop(unresolved_spr_ana_df[unresolved_spr_ana_df.last_word == 1].index)

df1 = unresolved_spr_ana_df[['word_pos', 'sent_pos', 'sent_nr', 'subj_nr', 'token', 'rt', 'spill']]
df2 = sbn_spr_ana_df[['word_pos', 'sent_pos', 'sent_nr', 'subj_nr', 'token', 'rt', 'spill']]
df1['resolved'] = 0
df2['resolved'] = 1

sbn_rt_resolved_df = pd.concat([df1, df2], ignore_index=True, sort=False)
enrich_with_ana_info(sbn_rt_resolved_df)

wrap_print('## RT ~ resolved')

df_name = 'sbn_ana_spr_rt_resolved_df'
save_for_R(sbn_rt_resolved_df, df_name)
write_r_for_ana(df_name, 'log(rt)', 'C(resolved) * sent_pos * C(reflexive) * word_pos')

df_name = 'sbn_ana_spr_spill_resolved_df'
sbn_spill_resolved_df = sbn_rt_resolved_df[sbn_rt_resolved_df.spill > 0]
save_for_R(sbn_spill_resolved_df, df_name)
write_r_for_ana(df_name, 'log(spill)', 'C(resolved) * sent_pos * C(reflexive) * word_pos')

wrap_print('## RT ~ distance')

df_name = 'sbn_ana_spr_rt_distance_df'
save_for_R(sbn_spr_ana_df, df_name)
write_r_for_ana(df_name, 'log(rt)', 'distance * C(reflexive) * word_pos')

df_name = 'sbn_ana_spr_spill_distance_df'
spill_sbn_spr_ana_distance_df = sbn_spr_ana_df[sbn_spr_ana_df.spill > 0]
save_for_R(spill_sbn_spr_ana_distance_df, df_name)
write_r_for_ana(df_name, 'log(spill)', 'distance * C(reflexive) * word_pos')

wrap_print('########################')
wrap_print('# FOR ET ANAPHORAS')
wrap_print('########################')

# Load SBN data
ori_manual_et_ana_df = pd.read_csv(to_abspath(data_folder, 'manual_ana_et_per_subj_rts.tsv'), sep='\t')
if skip_first_last_for_ana:
  ori_manual_et_ana_df['last_word'] = ori_manual_et_ana_df.token.str.endswith('.')
  ori_manual_et_ana_df.last_word = ori_manual_et_ana_df.last_word.astype(int)
unresolved_et_ana_df = ori_manual_et_ana_df[ori_manual_et_ana_df.distance == '?']

ori_sbn_et_ana_df = pd.read_csv(to_abspath(data_folder, 'sbn_ana_et_per_subj_rts.tsv'), sep='\t')
# clean up data
sbn_et_ana_df = ori_sbn_et_ana_df.drop(ori_sbn_et_ana_df[ori_sbn_et_ana_df.distance > 0].index)
enrich_with_ana_info(sbn_et_ana_df)

if skip_first_last_for_ana:
  # Exclude first and last word
  sbn_et_ana_df = sbn_et_ana_df.drop(sbn_et_ana_df[sbn_et_ana_df.word_pos == 1].index)
  sbn_et_ana_df = sbn_et_ana_df.drop(sbn_et_ana_df[sbn_et_ana_df.last_word == 1].index)
  unresolved_et_ana_df = unresolved_et_ana_df.drop(unresolved_et_ana_df[unresolved_et_ana_df.word_pos == 1].index)
  unresolved_et_ana_df = unresolved_et_ana_df.drop(unresolved_et_ana_df[unresolved_et_ana_df.last_word == 1].index)

unresolved_et_ana_df['resolved'] = 0
sbn_et_ana_df['resolved'] = 1

combo_et_ana_df = pd.concat([
  unresolved_et_ana_df[['word_pos', 'sent_pos', 'sent_nr', 'subj_nr', 'token', 'resolved', 'rt_fp', 'spill_fp']],
  sbn_et_ana_df[['word_pos', 'sent_pos', 'sent_nr', 'subj_nr', 'token', 'resolved', 'rt_fp', 'spill_fp']]
], ignore_index=True, sort=False)
enrich_with_ana_info(combo_et_ana_df)

wrap_print('## skip ~ resolved')

combo_et_ana_df['target_skipped'] = combo_et_ana_df['rt_fp'] == 0
combo_et_ana_df.target_skipped = combo_et_ana_df.target_skipped.astype(int)

skip_rate_fixed_effects = 'C(resolved) * sent_pos * C(reflexive) * word_pos'

df_name = 'sbn_ana_et_rt_skipped_resolved_df'
save_for_R(combo_et_ana_df, df_name)
write_r_for_ana(df_name, 'target_skipped', skip_rate_fixed_effects)

combo_et_ana_df['spill_skipped'] = combo_et_ana_df['spill_fp'] == 0
combo_et_ana_df.spill_skipped = combo_et_ana_df.spill_skipped.astype(int)
spill_combo_et_ana_df = combo_et_ana_df[combo_et_ana_df.spill_fp >= 0]

df_name = 'sbn_ana_et_spill_skipped_resolved_df'
save_for_R(spill_combo_et_ana_df, df_name)
write_r_for_ana(df_name, 'spill_skipped', skip_rate_fixed_effects)

wrap_print('## (non_reflexive) skip ~ resolved')

non_reflexive_combo_et_ana_df = combo_et_ana_df.drop(combo_et_ana_df[combo_et_ana_df.reflexive == 'TRUE'].index)
skip_rate_fixed_effects = 'C(resolved) * sent_pos * word_pos'

df_name = 'sbn_ana_et_rt_skipped_resolved_non_reflexive_df'
save_for_R(non_reflexive_combo_et_ana_df, df_name)
write_r_for_ana(df_name, 'target_skipped', skip_rate_fixed_effects)

non_reflexive_spill_combo_et_ana_df = non_reflexive_combo_et_ana_df[non_reflexive_combo_et_ana_df.spill_fp >= 0]

df_name = 'sbn_ana_et_spill_skipped_resolved_non_reflexive_df'
save_for_R(non_reflexive_spill_combo_et_ana_df, df_name)
write_r_for_ana(df_name, 'spill_skipped', skip_rate_fixed_effects)

wrap_print('## skip ~ distance')

sbn_et_ana_df['target_skipped'] = sbn_et_ana_df['rt_fp'] == 0
sbn_et_ana_df.target_skipped = sbn_et_ana_df.target_skipped.astype(int)

df_name = 'sbn_ana_et_rt_skipped_distance_df'
save_for_R(sbn_et_ana_df, df_name)
write_r_for_ana(df_name, 'target_skipped', 'distance * C(reflexive) * word_pos')

sbn_et_ana_df['spill_skipped'] = sbn_et_ana_df['spill_fp'] == 0
sbn_et_ana_df.spill_skipped = sbn_et_ana_df.spill_skipped.astype(int)
spill_sbn_et_ana_df = sbn_et_ana_df[sbn_et_ana_df.spill_fp >= 0]

df_name = 'sbn_ana_et_spill_skipped_distance_df'
save_for_R(spill_sbn_et_ana_df, df_name)
write_r_for_ana(df_name, 'spill_skipped', 'distance * C(reflexive) * word_pos')

wrap_print('## RT ~ resolved')

non_skipped_rt_combo_et_ana_df = combo_et_ana_df[combo_et_ana_df.rt_fp > 0]

df_name = 'sbn_ana_et_rt_resolved_df'
save_for_R(non_skipped_rt_combo_et_ana_df, df_name)
write_r_for_ana(df_name, 'log(rt_fp)', 'C(resolved) * sent_pos * C(reflexive) * word_pos')

non_skipped_spill_combo_et_ana_df = combo_et_ana_df[combo_et_ana_df.spill_fp > 0]

df_name = 'sbn_ana_et_spill_resolved_df'
save_for_R(non_skipped_spill_combo_et_ana_df, df_name)
write_r_for_ana(df_name, 'log(spill_fp)', 'C(resolved) * sent_pos * C(reflexive) * word_pos')

wrap_print('## RT ~ distance')

non_skipped_rt_sbn_et_ana_df = sbn_et_ana_df[sbn_et_ana_df.rt_fp > 0]

df_name = 'sbn_ana_et_rt_distance_df'
save_for_R(non_skipped_rt_sbn_et_ana_df, df_name)
write_r_for_ana(df_name, 'log(rt_fp)', 'distance * C(reflexive) * word_pos')

non_skipped_spill_sbn_et_ana_df = sbn_et_ana_df[sbn_et_ana_df.spill_fp > 0]

df_name = 'sbn_ana_et_spill_distance_df'
save_for_R(non_skipped_spill_sbn_et_ana_df, df_name)
write_r_for_ana(df_name, 'log(spill_fp)', 'distance * C(reflexive) * word_pos')

wrap_print('########################')
wrap_print('# FOR SPR ROLES')
wrap_print('########################')

ori_sbn_spr_role_df = pd.read_csv(to_abspath(data_folder, 'sbn_verb_role_spr_per_subj_rts.tsv'), sep='\t')

# clean up data
sbn_spr_role_df = ori_sbn_spr_role_df.drop(ori_sbn_spr_role_df[ori_sbn_spr_role_df.closest_role == '-'].index)
enrich_with_role_info(sbn_spr_role_df)

wrap_print('## rt ~ closest_distance')

df_name = 'sbn_role_spr_rt_closest_distance_df'
save_for_R(sbn_spr_role_df, df_name)
write_r_for_role(df_name, 'log(rt)', 'closest_distance * word_pos', 'closest_role')

spill_sbn_spr_role_df = sbn_spr_role_df[sbn_spr_role_df.spill > 0]

df_name = 'sbn_role_spr_spill_closest_distance_df'
save_for_R(spill_sbn_spr_role_df, df_name)
write_r_for_role(df_name, 'log(spill)', 'closest_distance * word_pos', 'closest_role')

wrap_print('## rt ~ furthest_distance')

df_name = 'sbn_role_spr_rt_furthest_distance_df'
save_for_R(sbn_spr_role_df, df_name)
write_r_for_role(df_name, 'log(rt)', 'furthest_distance * word_pos', 'furthest_role')

spill_sbn_spr_role_df = sbn_spr_role_df[sbn_spr_role_df.spill > 0]

df_name = 'sbn_role_spr_spill_furthest_distance_df'
save_for_R(spill_sbn_spr_role_df, df_name)
write_r_for_role(df_name, 'log(spill)', 'furthest_distance * word_pos', 'furthest_role')

wrap_print('########################')
wrap_print('# FOR ET ROLES')
wrap_print('########################')

ori_sbn_et_role_df = pd.read_csv(to_abspath(data_folder, 'sbn_verb_role_et_per_subj_rts.tsv'), sep='\t')

# clean up data
sbn_et_role_df = ori_sbn_et_role_df.drop(ori_sbn_et_role_df[ori_sbn_et_role_df.closest_role == '-'].index)
enrich_with_role_info(sbn_et_role_df)

wrap_print('## skip ~ closest_distance')

sbn_et_role_df['target_skipped'] = sbn_et_role_df['rt_fp'] == 0
sbn_et_role_df.target_skipped = sbn_et_role_df.target_skipped.astype(int)

df_name = 'sbn_role_et_rt_skipped_closest_distance_df'
save_for_R(sbn_et_role_df, df_name)
write_r_for_role(df_name, 'target_skipped', 'closest_distance * word_pos', 'closest_role')

spill_sbn_et_role_df = sbn_et_role_df[sbn_et_role_df.spill_fp >= 0]
spill_sbn_et_role_df['spill_skipped'] = spill_sbn_et_role_df['spill_fp'] == 0
spill_sbn_et_role_df.spill_skipped = spill_sbn_et_role_df.spill_skipped.astype(int)

df_name = 'sbn_role_et_spill_skipped_closest_distance_df'
save_for_R(spill_sbn_et_role_df, df_name)
write_r_for_role(df_name, 'spill_skipped', 'closest_distance * word_pos', 'closest_role')

wrap_print('## skip ~ furthest_distance')

df_name = 'sbn_role_et_rt_skipped_furthest_distance_df'
save_for_R(sbn_et_role_df, df_name)
write_r_for_role(df_name, 'target_skipped', 'furthest_distance * word_pos', 'furthest_role')

df_name = 'sbn_role_et_spill_skipped_furthest_distance_df'
save_for_R(spill_sbn_et_role_df, df_name)
write_r_for_role(df_name, 'spill_skipped', 'furthest_distance * word_pos', 'furthest_role')

wrap_print('## rt ~ closest_distance')

non_skipped_sbn_et_role_df = sbn_et_role_df[sbn_et_role_df.rt_fp > 0]

df_name = 'sbn_role_et_rt_closest_distance_df'
save_for_R(non_skipped_sbn_et_role_df, df_name)
write_r_for_role(df_name, 'log(rt_fp)', 'closest_distance * word_pos', 'closest_role')

non_skipped_spill_sbn_et_role_df = spill_sbn_et_role_df[spill_sbn_et_role_df.spill_fp > 0]

df_name = 'sbn_role_et_spill_closest_distance_df'
save_for_R(non_skipped_spill_sbn_et_role_df, df_name)
write_r_for_role(df_name, 'log(spill_fp)', 'closest_distance * word_pos', 'closest_role')

wrap_print('## rt ~ furthest_distance')

df_name = 'sbn_role_et_rt_furthest_distance_df'
save_for_R(non_skipped_sbn_et_role_df, df_name)
write_r_for_role(df_name, 'log(rt_fp)', 'furthest_distance * word_pos', 'furthest_role')

df_name = 'sbn_role_et_spill_furthest_distance_df'
save_for_R(non_skipped_spill_sbn_et_role_df, df_name)
write_r_for_role(df_name, 'log(spill_fp)', 'furthest_distance * word_pos', 'furthest_role')

wrap_print('########################')
wrap_print('# FOR SPR STORAGE')
wrap_print('########################')

ori_sbn_spr_storage_df = pd.read_csv(to_abspath(data_folder, 'sbn_verb_storage_spr_per_subj_rts.tsv'), sep='\t')
sbn_spr_storage_df = ori_sbn_spr_storage_df
# clean up data
enrich_with_storage_info(sbn_spr_storage_df)

wrap_print('## rt ~ neg * pos')

df_name = 'sbn_storage_spr_rt_neg_pos_df'
save_for_R(sbn_spr_storage_df, df_name)
write_r_for_storage(df_name, 'log(rt)', 'nr_neg_roles * nr_pos_roles * word_pos')

spill_sbn_spr_storage_df = sbn_spr_storage_df[sbn_spr_storage_df.spill > 0]

df_name = 'sbn_storage_spr_spill_neg_pos_df'
save_for_R(spill_sbn_spr_storage_df, df_name)
write_r_for_storage(df_name, 'log(spill)', 'nr_neg_roles * nr_pos_roles * word_pos')

wrap_print('########################')
wrap_print('# FOR ET STORAGE')
wrap_print('########################')

ori_sbn_et_storage_df = pd.read_csv(to_abspath(data_folder, 'sbn_verb_storage_et_per_subj_rts.tsv'), sep='\t')
sbn_et_storage_df = ori_sbn_et_storage_df
# clean up data
enrich_with_storage_info(sbn_et_storage_df)

wrap_print('## skip ~ neg_pos')

sbn_et_storage_df['target_skipped'] = sbn_et_storage_df['rt_fp'] == 0
sbn_et_storage_df.target_skipped = sbn_et_storage_df.target_skipped.astype(int)

df_name = 'sbn_storage_et_rt_skipped_neg_pos_df'
save_for_R(sbn_et_storage_df, df_name)
write_r_for_storage(df_name, 'target_skipped', 'nr_neg_roles * nr_pos_roles * word_pos')

spill_sbn_et_storage_df = sbn_et_storage_df[sbn_et_storage_df.spill_fp >= 0]
spill_sbn_et_storage_df['spill_skipped'] = spill_sbn_et_storage_df['spill_fp'] == 0
spill_sbn_et_storage_df.spill_skipped = spill_sbn_et_storage_df.spill_skipped.astype(int)

df_name = 'sbn_storage_et_spill_skipped_neg_pos_df'
save_for_R(spill_sbn_et_storage_df, df_name)
write_r_for_storage(df_name, 'spill_skipped', 'nr_neg_roles * nr_pos_roles * word_pos')

wrap_print('## skip ~ total')

df_name = 'sbn_storage_et_rt_skipped_total_df'
save_for_R(sbn_et_storage_df, df_name)
write_r_for_storage(df_name, 'target_skipped', 'nr_total_roles * word_pos')

df_name = 'sbn_storage_et_spill_skipped_total_df'
save_for_R(spill_sbn_et_storage_df, df_name)
write_r_for_storage(df_name, 'spill_skipped', 'nr_total_roles * word_pos')

wrap_print('## rt ~ neg_pos')

non_skipped_sbn_et_storage_df = sbn_et_storage_df[sbn_et_storage_df.rt_fp > 0]

df_name = 'sbn_storage_et_rt_neg_pos_df'
save_for_R(non_skipped_sbn_et_storage_df, df_name)
write_r_for_storage(df_name, 'log(rt_fp)', 'nr_neg_roles * nr_pos_roles * word_pos')

non_skipped_spill_sbn_et_storage_df = spill_sbn_et_storage_df[spill_sbn_et_storage_df.spill_fp > 0]

df_name = 'sbn_storage_et_spill_neg_pos_df'
save_for_R(non_skipped_spill_sbn_et_storage_df, df_name)
write_r_for_storage(df_name, 'log(spill_fp)', 'nr_neg_roles * nr_pos_roles * word_pos')

wrap_print('## rt ~ total')

df_name = 'sbn_storage_et_rt_total_df'
save_for_R(non_skipped_sbn_et_storage_df, df_name)
write_r_for_storage(df_name, 'log(rt_fp)', 'nr_total_roles * word_pos')

df_name = 'sbn_storage_et_spill_total_df'
save_for_R(non_skipped_spill_sbn_et_storage_df, df_name)
write_r_for_storage(df_name, 'log(spill_fp)', 'nr_total_roles * word_pos')

today = datetime.today().strftime('%Y%m%d-%H%M%S')
flush_clean_wrap_print(to_abspath(base_folder, f'script/1_prep-r-code_{today}.txt'))
