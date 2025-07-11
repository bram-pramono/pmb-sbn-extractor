import csv
import re
from datetime import datetime

from script.sbnutils import stimuli_folder, data_folder, report_folder
from script.utils import to_abspath

print_acc = []


def wrap_print(*messages):
  joined_message = ' '.join(messages) + '\n'
  print_acc.append(joined_message.replace('\n\n', '\n'))
  print(messages)


def flush_clean_wrap_print(file_path):
  with open(file_path, 'w') as out:
    out.writelines(print_acc)
  print_acc.clear()

stimuli_ref = {}
with open(to_abspath(stimuli_folder, 'stimuli.txt')) as raw_file:
  csv_reader = csv.DictReader(raw_file, delimiter='\t')
  stimuli_ref = {row['sent_nr']: row for row in csv_reader}

manual_ana_ref = {}
with open(to_abspath(data_folder, 'manual-anaphora.tsv')) as raw_file:
  csv_reader = csv.DictReader(raw_file, delimiter='\t')
  manual_ana_ref = {row['sent_nr']: row for row in csv_reader}


def extract_last_ana_match(ana_items):
  ana_item = ana_items.pop(0).strip()
  return ana_item, re.match('([a-zA-Z\'\.,]+)\[(\d+)\]([\{\[].+[\}\]])?\(([+\-0-9\?/ ]+)( \+ [+\-0-9\?/]+)?\)', ana_item)


line_to_write = None
lines_to_write = []

for sent_nr, row in manual_ana_ref.items():
  row_anas = row['non-12-per_anaphoras']
  if row_anas != '-' and row_anas != "'s[us](?)":
    sent = stimuli_ref[sent_nr]['sentence']
    sent_tokens = sent.split(' ')
    copy_sent_tokens = list(sent_tokens)
    row_ana_items = row_anas.split(';')

    ana_idxs = []
    special_anas = []
    idx = 0
    last_ana_item, last_ana_match = extract_last_ana_match(row_ana_items)
    while len(copy_sent_tokens) > 0:
      if last_ana_item in ["ana-we'll[9](?)", 'ana-the man[14](-8)', 'ana-the chopping block[13](-10)']:
        if last_ana_item == "ana-we'll[9](?)":
          special_anas.append((idx, last_ana_item, '?', None, None, idx))
        if last_ana_item == 'ana-the man[14](-8)':
          special_anas.append((idx, last_ana_item, 8, 6, 'man', idx))
        if last_ana_item == 'ana-the chopping block[13](-10)':
          special_anas.append((idx, last_ana_item, 10, 3, 'block', idx))
        if len(row_ana_items) == 0:
          break
        last_ana_item, last_ana_match = extract_last_ana_match(row_ana_items)
        continue
      token = copy_sent_tokens.pop(0)
      match_groups = last_ana_match.groups()
      sent_idx = match_groups[1]
      if match_groups[0] == token and last_ana_match is not None:
        target_idx = match_groups[3]
        if target_idx == '?' or '/' in target_idx or ' + ' in target_idx:
          target_idx = None
        elif target_idx.startswith('+'):
          target_idx = idx + int(target_idx.replace('+', ''))
        elif target_idx.startswith('-'):
          target_idx = idx - int(target_idx.replace('-', ''))
        else:
          raise Exception("WRONG!!!")

        distance = match_groups[3]
        ana_idxs.append((idx, token, distance, target_idx, None if target_idx is None else sent_tokens[target_idx], sent_idx))
        if len(row_ana_items) == 0:
          break
        last_ana_item, last_ana_match = extract_last_ana_match(row_ana_items)

      idx += 1

    line_to_write = dict(
      sent_nr=sent_nr,
      indexed_anaphoras=None)
    if len(ana_idxs) > 0:
      wrap_print('sent', sent_nr, 'ana_idxs:', str(ana_idxs))
      ana_idxs.extend(special_anas)
      line_to_write['indexed_anaphoras'] = str(ana_idxs)
    lines_to_write.append(line_to_write)

today = datetime.today().strftime('%Y%m%d-%H%M%S')
flush_clean_wrap_print(to_abspath(report_folder, f'report-0_index-manual-anaphoras_{today}.txt'))

with open(to_abspath(data_folder, f'indexed-manual-anaphoras_{today}.tsv'), 'w') as out_file:
  w = csv.DictWriter(out_file, line_to_write.keys(), delimiter='\t')
  w.writeheader()
  w.writerows(lines_to_write)
