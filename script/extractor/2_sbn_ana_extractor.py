import csv
import os
import re
from datetime import datetime

from script.sbnutils import extract_sbn_integration, determine_ori_sent_token_idxs_based_on_sbn, parse_research_data, clean_up_sbn_anas, \
  stimuli_folder, data_folder, report_folder
from script.utils import to_abspath, load_indexed_manual_anaphoras, load_pmb_ids, load_spr_rt_with_subj_by_keys, \
  load_et_rt_with_subj_by_keys, get_et_sent_nrs

ANA_WORDS = ["he'd", 'himself.', 'herself', 'her.', "he'll", 'him.', 'my', 'she', 'they', 'his', 'itself.', 'him', 'Paul', 'me.', "they'll", 'her',
             'himself', 'them.', 'their', 'you', 'he', 'her,', 'that.', 'it', 'our', 'your', 'Charlie', 'it.', 'them']

print_acc = []


def wrap_print(*messages):
  joined_message = ' '.join(messages) + '\n'
  print_acc.append(joined_message.replace('\n\n', '\n'))
  print(messages)


def flush_clean_wrap_print(file_path):
  with open(file_path, 'w') as out:
    out.writelines(print_acc)
  print_acc.clear()


if __name__ == '__main__':
  stimuli_ref = parse_research_data(stimuli_folder)
  manual_ref = load_indexed_manual_anaphoras()
  pmb_id_ref = load_pmb_ids()

  sbn_drs_folder = to_abspath(data_folder, f'for-analysis')
  indexed_aligned_lines = []
  sbn_ana_distance_with_rt_list = []

  skipped_pmb_ids = []

  for filename in sorted(os.listdir(sbn_drs_folder)):
    indexed_aligned_line = {}
    indexed_aligned_lines.append(indexed_aligned_line)
    src = to_abspath(sbn_drs_folder, filename)
    sbn_anas = []
    with open(src) as scraped_file:
      pmb_id = filename.replace(".txt", "")
      file_lines = scraped_file.readlines()
      sent = file_lines[0][2:].strip()
      sent_tokens = sent.split(' ')
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
      elif filename == 'd0352_p35.txt':
        skipped_pmb_ids.append(pmb_id)
        wrap_print(f'!! has cataphora marked as anaphora. We skip this!')
      else:
        # Need to match anaphoras out of SBN to sent
        if 'ANA' in [x[3] for x in integration_map] or 'person.n.01 EQU' in [sbn_lines_list[x[2]][0] + ' ' + x[3] for x in integration_map]:
          wrap_print(filename, '-' * 10)
          anaphora_links = [x for x in integration_map if x[3] == 'ANA' or sbn_lines_list[x[2]][0] + ' ' + x[3] == 'person.n.01 EQU']
          for indent, connector_id, idx, role, target_idx, distance, ori_token_span in anaphora_links:
            if ori_token_span is not None:
              ana_sent_idxs, ana_tokens = determine_ori_sent_token_idxs_based_on_sbn(sent_nr, ori_token_span[0], ori_token_span[1])
              wrap_print(f'ana{"#" if len(ana_sent_idxs) > 1 else ""}: role={role}; ana_sent_idxs={ana_sent_idxs}; ana_tokens={ana_tokens}')
              sent_ana_idx = ana_sent_idxs[0]
              sent_ana_token = ana_tokens[0]
              if len(ana_tokens) > 1:
                try:
                  ana_token_idx = next(idx for idx, token in enumerate(ana_tokens) if token in ANA_WORDS)
                  sent_ana_idx, sent_ana_token = (ana_sent_idxs[ana_token_idx], ana_tokens[ana_token_idx])
                except StopIteration as e:
                  if f'{sent_nr}_{str(ana_sent_idxs)}_{str(ana_tokens)}' == "160_[5, 6]_['but', 'I']":
                    sent_ana_idx = 6
                    sent_ana_token = 'I'
                  else:
                    sent_ana_idx = ana_sent_idxs
                    sent_ana_token = ana_tokens

              ante_sbn_info = non_connector_sbn_lines[target_idx]
              if ante_sbn_info.word_info.word == '':
                wrap_print(f'Antecedent does not have a word. ante = {str(ante_sbn_info)}')
                continue
              ante_sent_idxs, ante_tokens = determine_ori_sent_token_idxs_based_on_sbn(sent_nr, ante_sbn_info.word_info.start_idx,
                                                                                       ante_sbn_info.word_info.end_idx)
              wrap_print(f'ante{"#" if len(ante_sent_idxs) > 1 else ""}: ante_sent_idxs={ante_sent_idxs}; ante_tokens={ante_tokens}')
              sent_ante_idx = ante_sent_idxs[0]
              sent_ante_token = ante_tokens[0]
              if len(ante_tokens) > 1:
                try:
                  ante_token_idx = next(idx for idx, token in enumerate(ante_tokens) if token.lower() in ANA_WORDS)
                  sent_ante_idx, sent_ante_token = (ante_sent_idxs[ante_token_idx], ante_tokens[ante_token_idx])
                except StopIteration as e:
                  sent_ante_idx = ante_sent_idxs
                  sent_ante_token = ante_tokens

              # NOTE: contents of sbn_anas = ana_name, ana_sbn_spans, ana_tokens, ante_name, ante_sbn_spans, ante_tokens, sbn_distance, sbn_roles
              sbn_anas.append((
                sbn_lines_list[idx][0],
                sent_ana_idx,
                sent_ana_token,
                sbn_lines_list[target_idx][0],
                sent_ante_idx,
                sent_ante_token,
                distance,
                sbn_lines_list[idx][4],
              ))

      clean_sbn_anas = clean_up_sbn_anas(sbn_anas)
      for ana_name, ana_token_idx, ana_tokens, ante_name, ante_token_idx, ante_tokens, sbn_distance, sbn_roles in clean_sbn_anas:
        sbn_ana_distance_with_rt_list.append({
          'sent_nr': sent_nr,
          'sent': sent,
          'last_word': 1 if ana_token_idx == len(sent_tokens) - 1 else 0,
          'ana_token_idx': ana_token_idx,
          'ana_token': ana_tokens,
          'ante_token_idx': ante_token_idx,
          'ante_token': ante_tokens,
          'distance': sbn_distance,
          'rt': 0,
        })

  wrap_print(f'{len(skipped_pmb_ids)} pmb records are skipped. The whole list can be seen below:')
  wrap_print(str(skipped_pmb_ids))

  to_exclude = ['I', 'my', 'you', 'your', 'Paul', 'Charlie']

  spr_data_with_subj = load_spr_rt_with_subj_by_keys()
  extracted_spr_sbn_data_with_subj = []

  et_data_with_subj = load_et_rt_with_subj_by_keys()
  et_sent_nrs = get_et_sent_nrs()
  extracted_et_sbn_data_with_subj = []

  sents_with_unresolved = set()

  for key, indexed_anaphoras in manual_ref.items():
    # NOTE!! There are indeed the same sent_idxs which are identical
    for ana_token_idx, token, distance, target_idx, target_token, sent_idx2 in indexed_anaphoras:
      if distance == '?':
        sent_nr = int(key)
        sents_with_unresolved.add(sent_nr)

  for idx, row in enumerate(sbn_ana_distance_with_rt_list):
    if row['ana_token'] not in to_exclude:
      word_pos = int(row['ana_token_idx']) + 1
      sent_nr = int(row['sent_nr'])

      # ###
      # Self-Paced Reading Data
      # ###

      rt_all_subj = spr_data_with_subj[sent_nr][word_pos]
      for subj_nr, (rt, sent_pos) in rt_all_subj.items():
        data_with_subj = {
          'sent_nr': sent_nr,
          'word_pos': word_pos,
          'sent_pos': sent_pos,
          'last_word': row['last_word'],
          'token': row['ana_token'],
          'sent_has_unresolved': sent_nr in sents_with_unresolved,
          'distance': row['distance'],
          'subj_nr': subj_nr,
          'rt': rt,
          'spill': -999
        }
        if word_pos + 1 in spr_data_with_subj[sent_nr]:
          data_with_subj['spill'] = spr_data_with_subj[sent_nr][word_pos + 1][subj_nr][0]
        extracted_spr_sbn_data_with_subj.append(data_with_subj)

    # ###
    # Eye Tracking Data
    # ###

    if sent_nr in et_sent_nrs:

      for subj_nr, (subj_rt_ff, subj_rt_fp, subj_rt_rb, subj_rt_gp, sent_pos) in et_data_with_subj[sent_nr][word_pos].items():
        combined_et_data_with_subj = {
          'sent_nr': sent_nr,
          'word_pos': word_pos,
          'sent_pos': sent_pos,
          'last_word': row['last_word'],
          'token': row['ana_token'],
          'sent_has_unresolved': sent_nr in sents_with_unresolved,
          'distance': row['distance'],
          'subj_nr': subj_nr,
          'rt_ff': subj_rt_ff,
          'rt_fp': subj_rt_fp,
          'rt_rb': subj_rt_rb,
          'rt_gp': subj_rt_gp,
          'spill_ff': -999,
          'spill_fp': -999,
          'spill_rb': -999,
          'spill_gp': -999,
        }
        if word_pos + 1 in et_data_with_subj[sent_nr]:
          combined_et_data_with_subj['spill_ff'] = et_data_with_subj[sent_nr][word_pos + 1][subj_nr][0]
          combined_et_data_with_subj['spill_fp'] = et_data_with_subj[sent_nr][word_pos + 1][subj_nr][1]
          combined_et_data_with_subj['spill_rb'] = et_data_with_subj[sent_nr][word_pos + 1][subj_nr][2]
          combined_et_data_with_subj['spill_gp'] = et_data_with_subj[sent_nr][word_pos + 1][subj_nr][3]
        extracted_et_sbn_data_with_subj.append(combined_et_data_with_subj)

  with open(to_abspath(data_folder, f'sbn_ana_spr_per_subj_rts.tsv'), 'w') as out_file:
    w = csv.DictWriter(out_file, extracted_spr_sbn_data_with_subj[0].keys(), delimiter='\t')
    w.writeheader()
    w.writerows(extracted_spr_sbn_data_with_subj)

  with open(to_abspath(data_folder, f'sbn_ana_et_per_subj_rts.tsv'), 'w') as out_file:
    w = csv.DictWriter(out_file, extracted_et_sbn_data_with_subj[0].keys(), delimiter='\t')
    w.writeheader()
    w.writerows(extracted_et_sbn_data_with_subj)

  today = datetime.today().strftime('%Y%m%d-%H%M%S')
  flush_clean_wrap_print(to_abspath(report_folder, f'2b_simple_sbn_extractor_{today}.txt'))
