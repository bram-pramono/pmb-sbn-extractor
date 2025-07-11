import difflib
import filecmp
import os
import re
import shutil
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from script.sbnutils import data_folder, report_folder
from script.utils import to_abspath


# I've added the UCL documents. They are in document d0349 for p30/p99, d0350 for p00 to p99 and d0351 for p00 to p38. In the explorer you can filter for subcorpus "UCL" to get only these documents.

def wrap_print(*messages):
  joined_message = ' '.join(messages) + '\n'
  print_acc.append(joined_message.replace('\n\n', '\n'))
  print(messages)


def flush_clean_wrap_print(file_path):
  with open(file_path, 'w') as out:
    out.writelines(print_acc)
  print_acc.clear()


def extract_incremental_drs(soup):
  incremental_drs_data = []
  wrap_print('Extracting incremental drs per token')

  def remove_ws(text):
    # text = re.sub(r"\t", "$", text)
    text = re.sub(r"\s+", "", text)
    # text = re.sub(r"\$", " ", text)
    return text

  def extract_drs(css_to_extract):
    for span in css_to_extract.select('.drs-pred-symbol'):
      sup = soup.new_tag('p')
      sup.string = ':'
      span.insert_after(sup)

    for framenet_rel in css_to_extract.select('.drs-rel-framenet'):
      framenet_rel.decompose()

    drs_labels = css_to_extract.select('td.drs-label')
    assert len(drs_labels) < 2, "expected 1 drs-label"

    return f"""
    <{drs_labels[0].getText()}>
    {[remove_ws(x.getText()) for x in css_to_extract.select('ul.drs-domain li.drs-domain-element')]}
    :
    {[remove_ws(x.getText()) for x in css_to_extract.select('ul.drs-conds li.drs-cond')]}
    </{drs_labels[0].getText()}>
    """

  def extract_text(selected_css):
    return ' '.join([remove_ws(x.getText()) for x in selected_css])

  lambda_tags = soup.select('table.lex')

  target_folder = 'tmp_data'
  if os.path.exists(target_folder):
    shutil.rmtree(target_folder)
  os.mkdir(target_folder)
  for idx, tag in enumerate(lambda_tags):
    tokens = extract_text(tag.select('tr[id^="tokens_"] strong'))
    drs_tag = tag.select('table.drs')
    if len(drs_tag) > 0:
      for table_drs in reversed(drs_tag):
        sup = soup.new_tag('p')
        sup.string = extract_drs(table_drs)
        table_drs.insert_after(sup)
        table_drs.decompose()

    incremental_drs_data.append('tokens:' + str(tokens))
    sem = extract_text(tag.select('td.sem'))
    incremental_drs_data.append(f'\nsem: {sem}')
    cat = extract_text(tag.select('td.category'))
    incremental_drs_data.append(f'\ncat: {cat}')
    incremental_drs_data.append('\n' + '-' * 10 + '\n')

  return incremental_drs_data


def scrape_franketal_data(target_base_folder, docs_to_scrape):
  global req_headers, count

  req_headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Host": "pmb.let.rug.nl",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Cookie": "PHPSESSID=m7eh4bqi7n52segmm316tsjspb; __utma=154227001.1956455504.1698312166.1698312166.1698312166.1; __utmc=154227001; __utmz=154227001.1698312166.1.1.utmcsr=(direct)|utmccn=(direct)|utmcmd=(none); __utmt=1; __utmb=154227001.7.10.1698312166"
  }

  def scrape_page(url, css_selectors: list):
    wrap_print(f'scraping {url}')
    html = requests.get(url, headers=req_headers).text
    soup = BeautifulSoup(html)
    return [str(soup.select(css_selector)).replace('[<pre>', '').replace('</pre>]', '') for css_selector in css_selectors]

  os.mkdir(target_base_folder)
  count = 0
  for doc_id, part in docs_to_scrape:
    url_text = f"https://pmb.let.rug.nl/explorer/explore.php?part={part:02d}&doc_id={doc_id}&type=raw&alignment_language=en"
    sent = scrape_page(url_text, ["#content pre"])[0]
    url_sbn = f"https://pmb.let.rug.nl/explorer/explore.php?part={part:02d}&doc_id={doc_id}&type=drs.xml&alignment_language=en"
    semantic_data = scrape_page(url_sbn, ["#drc pre", "#sbn pre"])
    url_der = f"https://pmb.let.rug.nl/explorer/explore.php?part={part:02d}&doc_id={doc_id}&type=der.xml&searchMode=direct"
    html = requests.get(url_der, headers=req_headers).text
    lambda_soup = BeautifulSoup(html)

    with open(f'{target_base_folder}/d{doc_id}_p{part:02d}.txt', 'w') as out:
      out.write('% ' + sent)
      out.write('\n\n')
      out.write(semantic_data[0])
      out.write('\n\n')
      out.write('% Sequence Box Notation\n\n')
      sbn_data = semantic_data[1].replace('<s>', ' --').replace('</s>', '--').split('\n')
      out.write('\n'.join([f'%SBN% {line}' for line in sbn_data if len(line.strip()) > 0]))
      out.write('\n\n')
      out.write('% Incremental DRS\n\n')
      out.writelines(extract_incremental_drs(lambda_soup))

    count += 1
    wrap_print(f"done ({count}/{len(docs_to_scrape)}) {doc_id}, {part}")

  wrap_print(f"Finished scraping {count} pages")


def scrape_data_sanity_check(target_folder):
  wrap_print('!' * 20)
  wrap_print("Running sanity check")
  count = 0
  files = sorted(os.listdir(target_folder))
  for file in files:
    with open(f'{target_folder}/{file}', 'r') as file_raw:
      if '%SBN%' not in file_raw.read():
        wrap_print(f'{file} is missing SBN')
        count += 1
  wrap_print(f'Found {count} files improperly scraped')
  wrap_print('!' * 20)


def has_scraped_data_diff_with_previous(new_folder, prev_folder):
  wrap_print(f"Comparing the new folder {new_folder} against {prev_folder}")
  wrap_print('*' * 20)
  found_diff = False

  prev_file_list = os.listdir(prev_folder)
  new_file_list = os.listdir(new_folder)

  list_diff = list(set(prev_file_list) - set(new_file_list))
  if len(list_diff) > 0:
    found_diff = True

  for prev_file in prev_file_list:
    for new_file in new_file_list:
      if (prev_file == new_file):
        prev_path = to_abspath(prev_folder, prev_file)
        new_path = to_abspath(new_folder, new_file)
        same = filecmp.cmp(prev_path, new_path, shallow=False)
        if not same:
          wrap_print(f'{new_file} has changed')
          wrap_print('-' * 20)
          found_diff = True

          with open(prev_path, 'r') as prev_raw_file:
            with open(new_path, 'r') as new_raw_file:
              content_diff = difflib.unified_diff(
                prev_raw_file.readlines(),
                new_raw_file.readlines(),
                fromfile='prev_raw_file',
                tofile='new_raw_file',
                n=1
              )
              for line in content_diff:
                wrap_print(line)
  return found_diff


def replace_prev_folder(new_folder, prev_folder):
  if os.path.exists(prev_folder):
    wrap_print(f'Removing {prev_folder}')
    shutil.rmtree(prev_folder)
  wrap_print(f'Copying {new_folder} to {prev_folder}')
  shutil.copytree(new_folder, prev_folder)


############ MAIN ###############
#################################
if __name__ == '__main__':
  print_acc = []
  today = datetime.today().strftime('%Y%m%d-%H%M%S')
  wrap_print(f"Running data collection and clean up at {today}")
  target_scrape_folder = to_abspath(data_folder, "scraped_data", today)
  prev_scrape_folder = to_abspath(data_folder, "scraped_data/latest")
  preparation_folder = to_abspath(data_folder, "for-analysis")

  docs = [
    # ("0349", 30, 99),
    # ("0350", 00, 99),
    # ("0351", 00, 38),

    ("0349", 30, 99),
    ("0350", 00, 99),
    ("0351", 00, 99),
    ("0352", 00, 99),
    ("0353", 00, 7),
  ]
  wrong_docs = [
    ("0349", 50),
    ("0349", 58),
    ("0350", 90),
    ("0351", 23),
    ("0351", 39),
    ("0351", 40),
    ("0351", 41),
    ("0351", 42),
    ("0351", 43),
    ("0351", 44),
    ("0351", 45),
    ("0351", 46),
    ("0351", 47),
    ("0351", 48),
    ("0351", 49),
    ("0351", 50),
    ("0352", 48),

    # ("0350", 17),  # missing annotations
    # ("0350", 96),  # missing annotations
    # ("0352", 23),  # missing annotations
  ]
  # d0350_p17.txt is smaller
  # d0350_p96.txt is smaller
  # d0352_p23.txt is smaller

  # 30 / 349 - 99 / 349
  # 00 / 350 - 99 / 350
  # 00 / 351 - 99 / 351
  # 00 / 352 - 99 / 352
  # 00 / 353 - 07 / 353

  correct_docs = [(doc[0], part) for doc in docs
                  for part in range(doc[1], doc[2] + 1)
                  if (doc[0], part) not in wrong_docs]

  # NOTE: The following cannot be scraped. On March 29th, the page contained empty drs clauses
  # https://pmb.let.rug.nl/explorer/explore.php?part=96&doc_id=0350&type=raw&alignment_language=en

  # https://pmb.let.rug.nl/explorer/explore.php?part=17&doc_id=0350&type=raw&alignment_language=en

  scrape_franketal_data(target_scrape_folder, correct_docs)
  scrape_data_sanity_check(target_scrape_folder)
  found_diff = has_scraped_data_diff_with_previous(target_scrape_folder, prev_scrape_folder)
  replace_prev_folder(target_scrape_folder, prev_scrape_folder)

  if found_diff:
    wrap_print(f'Differences found. Updating data on "{preparation_folder}"')
    shutil.copytree(target_scrape_folder, preparation_folder, dirs_exist_ok=True)
  else:
    wrap_print(f'No difference found.')
    wrap_print(f'Removing {target_scrape_folder}')
    shutil.rmtree(target_scrape_folder)

  flush_clean_wrap_print(to_abspath(report_folder, f'report-1_scrape-pmb-data_{today}.txt'))
