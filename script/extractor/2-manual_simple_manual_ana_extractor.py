import csv

from script.sbnutils import parse_research_data
from script.utils import to_abspath, load_indexed_manual_anaphoras, load_pmb_ids, load_avg_spr_rt_by_keys, load_spr_rt_with_subj_by_keys, \
  load_et_rt_with_subj_by_keys, load_avg_et_rt_by_keys, load_et_with_subj_df

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
  base_folder = "/home/pramono/work/drs/pmb-sbn-extractor"
  report_folder = to_abspath(base_folder, 'report')
  data_folder = to_abspath(report_folder, 'data')

  stimuli_folder = to_abspath(base_folder, 'data/frank_etal/')
  stimuli_ref = parse_research_data(stimuli_folder)
  manual_ref = load_indexed_manual_anaphoras()
  pmb_id_ref = load_pmb_ids()

  spr_data = load_avg_spr_rt_by_keys()
  spr_data_with_subj = load_spr_rt_with_subj_by_keys()
  extracted_spr_manual_data_with_subj = []

  et_data = load_avg_et_rt_by_keys()
  et_data_with_subj = load_et_rt_with_subj_by_keys()
  et_sent_nrs = load_et_with_subj_df()['sent_nr'].unique()
  extracted_et_manual_data_with_subj = []

  sents_with_unresolved = set()

  for key, indexed_anaphoras in manual_ref.items():
    # NOTE!! There are indeed the same sent_idxs which are identical
    for ana_token_idx, token, distance, target_idx, target_token, sent_idx2 in indexed_anaphoras:
      if distance == '?':
        sent_nr = int(key)
        sents_with_unresolved.add(sent_nr)

  for key, indexed_anaphoras in manual_ref.items():
    sent_nr = int(key)
    # NOTE!! There are indeed the same sent_idxs which are identical
    for ana_token_idx, token, distance, target_idx, target_token, sent_idx2 in indexed_anaphoras:
      word_pos = int(ana_token_idx) + 1

      rt_spr_subj = spr_data_with_subj[sent_nr][word_pos]
      for subj_nr, spr_rt in rt_spr_subj.items():
        combined_spr_data_with_subj = {
          'sent_nr': sent_nr,
          'word_pos': word_pos,
          'token': token,
          'sent_has_unresolved': sent_nr in sents_with_unresolved,
          'distance': distance,
          'subj_nr': subj_nr,
          'rt': spr_rt,
          'spill': -999
        }
        if word_pos + 1 in spr_data_with_subj[sent_nr]:
          combined_spr_data_with_subj['spill'] = spr_data_with_subj[sent_nr][word_pos + 1][subj_nr]
        extracted_spr_manual_data_with_subj.append(combined_spr_data_with_subj)

      # ###
      # Eye Tracking Data
      # ###

      if sent_nr in et_sent_nrs:

        for subj_nr, (subj_rt_ff, subj_rt_fp, subj_rt_rb, subj_rt_gp) in et_data_with_subj[sent_nr][word_pos].items():
          combined_et_data_with_subj = {
            'sent_nr': sent_nr,
            'word_pos': word_pos,
            'token': token,
            'sent_has_unresolved': sent_nr in sents_with_unresolved,
            'distance': distance,
            'subj_nr': subj_nr,
            'rt_ff': et_data_with_subj[sent_nr][word_pos][subj_nr][0],
            'rt_fp': et_data_with_subj[sent_nr][word_pos][subj_nr][1],
            'rt_rb': et_data_with_subj[sent_nr][word_pos][subj_nr][2],
            'rt_gp': et_data_with_subj[sent_nr][word_pos][subj_nr][3],
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
          extracted_et_manual_data_with_subj.append(combined_et_data_with_subj)

  with open(to_abspath(data_folder, f'manual_ana_spr_per_subj_rts.tsv'), 'w') as out_file:
    w = csv.DictWriter(out_file, extracted_spr_manual_data_with_subj[0].keys(), delimiter='\t')
    w.writeheader()
    w.writerows(extracted_spr_manual_data_with_subj)

  with open(to_abspath(data_folder, f'manual_ana_et_per_subj_rts.tsv'), 'w') as out_file:
    w = csv.DictWriter(out_file, extracted_et_manual_data_with_subj[0].keys(), delimiter='\t')
    w.writeheader()
    w.writerows(extracted_et_manual_data_with_subj)
