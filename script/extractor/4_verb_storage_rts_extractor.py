import copy
import csv
import os
import re
from datetime import datetime

from script.sbnutils import determine_ori_sent_token_idxs_based_on_sbn, parse_research_data, extract_sbn_integration, stimuli_folder, data_folder, \
  report_folder
from script.utils import to_abspath, load_indexed_manual_anaphoras, load_pmb_ids, load_spr_rt_with_subj_by_keys, \
  load_et_rt_with_subj_by_keys, load_et_with_subj_df

print_acc = []


def wrap_print(*messages):
  joined_message = ' '.join(messages) + '\n'
  print_acc.append(joined_message.replace('\n\n', '\n'))
  print(messages)


def flush_clean_wrap_print(file_path):
  with open(file_path, 'w') as out:
    out.writelines(print_acc)
  print_acc.clear()


def extract_verbs_and_storage_changes(non_connector_sbn_lines):
  global pmb_id, sent_nr
  roles_data = []
  sbn_verb_lines = [(idx, line) for idx, line in enumerate(non_connector_sbn_lines) if '.v.' in line.sbn_word]
  for idx, verb_line in sbn_verb_lines:
    if verb_line.word_info.word == '':
      wrap_print(f'Skipping sbn verb line of {str(verb_line)}')
      continue
    wrap_print('-' * 3)
    wrap_print(f'{verb_line.sbn_word} - {verb_line.word_info.word} ({verb_line.word_info.word_with_context})')

    sent_idxs, sent_tokens = determine_ori_sent_token_idxs_based_on_sbn(sent_nr, verb_line.word_info.start_idx, verb_line.word_info.end_idx)
    if len(sent_tokens) > 1:
      clean_sent_tokens = [x.replace('.', '').replace(',', '') for x in sent_tokens]
      word_to_find = verb_line.word_info.word
      if ' ' in word_to_find:
        word_to_find = word_to_find.split(' ')[0]
      word_idx = clean_sent_tokens.index(word_to_find)
      word_pos = sent_idxs[word_idx] + 1
      target_token = word_to_find
    else:
      word_pos = sent_idxs[0] + 1
      target_token = sent_tokens[0]

    negative_roles = [(x, int(y)) for x, y in verb_line.roles if y.startswith('-') and x != 'Time']
    positive_roles = [(x, int(y)) for x, y in verb_line.roles if y.startswith('+') and x != 'Time']

    roles_data.append(dict(
      sent_nr=sent_nr,  # this is the index of this verb in sbn
      sbn_verb_pos=idx,  # this is the index of this verb in sbn
      nr_neg_roles=len(negative_roles),
      nr_pos_roles=len(positive_roles),
      word_pos=word_pos,
      token=target_token,
      sent_idxs=sent_idxs,
      sent_tokens=sent_tokens,
    ))

  wrap_print('=' * 10)
  return roles_data


if __name__ == '__main__':
  stimuli_ref = parse_research_data(stimuli_folder)
  manual_ref = load_indexed_manual_anaphoras()
  pmb_id_ref = load_pmb_ids()

  spr_data_with_subj = load_spr_rt_with_subj_by_keys()

  et_data_with_subj = load_et_rt_with_subj_by_keys()
  et_sent_nrs = load_et_with_subj_df()['sent_nr'].unique()

  extracted_spr_sbn_data_with_subj = []
  extracted_et_sbn_data_with_subj = []

  sbn_drs_folder = to_abspath(data_folder, f'for-analysis')
  indexed_aligned_lines = []

  skipped_pmb_ids = []

  for filename in sorted(os.listdir(sbn_drs_folder)):
    indexed_aligned_line = {}
    indexed_aligned_lines.append(indexed_aligned_line)
    src = to_abspath(sbn_drs_folder, filename)
    with open(src) as scraped_file:
      pmb_id = filename.replace(".txt", "")
      file_lines = scraped_file.readlines()
      sent = file_lines[0][2:].strip()
      stimulus_info = stimuli_ref[sent]
      sent_nr = stimulus_info['sent_nr']
      file_content = ''.join(file_lines)
      file_content = file_content.split('% Sequence Box Notation')
      data_to_process = file_content[1].split('% Incremental DRS')
      sbn_raw_text = data_to_process[0].strip()
      # lambda_data = data_to_process[1].strip()

      context_map, integration_map, sbn_lines_list, full_sbn_info_list = extract_sbn_integration(sent, sbn_raw_text)
      non_connector_sbn_lines = [x for x in full_sbn_info_list if x.sbn_word is not None]

      # check sbn parsing order. If the sentence is not in order. report this as misparsing and skip.
      sbn_words = [x.word_info.word_with_context.replace('--', '') for x in full_sbn_info_list if 'word_info' in x]
      sbn_parsing_in_order = sent.replace(' ', '') == re.sub(' +', '', ''.join(sbn_words))

      wrap_print(f'pmb_id: {pmb_id} sent_nr: {sent_nr}')
      if not sbn_parsing_in_order:
        skipped_pmb_ids.append(pmb_id)
        wrap_print(f'!! is not parsed in order of the sentence or has an issue with the anaphora. We skip this! See comparison:')
        wrap_print(f'sent = {sent.replace(" ", "")}')
        wrap_print(f'sbn  = {re.sub(" +", "", "".join(sbn_words))}')
      else:
        sbn_verb_storage_data = extract_verbs_and_storage_changes(non_connector_sbn_lines)
        sent_nr = int(sent_nr)
        for verb_storage_data in sbn_verb_storage_data:
          word_pos = verb_storage_data['word_pos']
          spr_rt_all_subj = spr_data_with_subj[sent_nr][word_pos]
          for subj_nr, (rt, sent_pos) in spr_rt_all_subj.items():
            spr_copy_storage_data = copy.deepcopy(verb_storage_data)
            spr_copy_storage_data['subj_nr'] = subj_nr
            spr_copy_storage_data['sent_pos'] = sent_pos
            spr_spill = -999
            if word_pos + 1 in spr_data_with_subj[sent_nr]:
              spr_spill = spr_data_with_subj[sent_nr][word_pos + 1][subj_nr][0]

            spr_copy_storage_data['rt'] = rt
            spr_copy_storage_data['spill'] = spr_spill
            extracted_spr_sbn_data_with_subj.append(spr_copy_storage_data)

          for subj_nr, (subj_rt_ff, subj_rt_fp, subj_rt_rb, subj_rt_gp, sent_pos) in et_data_with_subj[sent_nr][word_pos].items():
            et_copy_storage_data = copy.deepcopy(verb_storage_data)
            et_copy_storage_data['subj_nr'] = subj_nr
            spr_copy_storage_data['sent_pos'] = sent_pos
            et_spill_ff = -999
            et_spill_fp = -999
            et_spill_rb = -999
            et_spill_gp = -999
            if word_pos + 1 in et_data_with_subj[sent_nr]:
              et_spill_ff = et_data_with_subj[sent_nr][word_pos + 1][subj_nr][0]
              et_spill_fp = et_data_with_subj[sent_nr][word_pos + 1][subj_nr][1]
              et_spill_rb = et_data_with_subj[sent_nr][word_pos + 1][subj_nr][2]
              et_spill_gp = et_data_with_subj[sent_nr][word_pos + 1][subj_nr][3]

            et_copy_storage_data['rt_ff'] = subj_rt_ff
            et_copy_storage_data['rt_fp'] = subj_rt_fp
            et_copy_storage_data['rt_rb'] = subj_rt_rb
            et_copy_storage_data['rt_gp'] = subj_rt_gp
            et_copy_storage_data['spill_ff'] = et_spill_ff
            et_copy_storage_data['spill_fp'] = et_spill_fp
            et_copy_storage_data['spill_rb'] = et_spill_rb
            et_copy_storage_data['spill_gp'] = et_spill_gp
            extracted_et_sbn_data_with_subj.append(et_copy_storage_data)

  wrap_print(f'{len(skipped_pmb_ids)} pmb records are skipped. The whole list can be seen below:')
  wrap_print(str(skipped_pmb_ids))

  with open(to_abspath(data_folder, f'sbn_verb_storage_spr_per_subj_rts.tsv'), 'w') as out_file:
    w = csv.DictWriter(out_file, extracted_spr_sbn_data_with_subj[0].keys(), delimiter='\t')
    w.writeheader()
    w.writerows(extracted_spr_sbn_data_with_subj)

  with open(to_abspath(data_folder, f'sbn_verb_storage_et_per_subj_rts.tsv'), 'w') as out_file:
    w = csv.DictWriter(out_file, extracted_et_sbn_data_with_subj[0].keys(), delimiter='\t')
    w.writeheader()
    w.writerows(extracted_et_sbn_data_with_subj)

  today = datetime.today().strftime('%Y%m%d-%H%M%S')
  flush_clean_wrap_print(to_abspath(report_folder, f'4_sbn_verb_storage_rts_extractor_{today}.txt'))
