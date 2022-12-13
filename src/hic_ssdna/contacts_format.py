#! /usr/bin/env python3

import numpy as np
import pandas as pd
import math
import sys
import getopt
from Bio.SeqIO.FastaIO import FastaIterator


def is_debug() -> bool:
    gettrace = getattr(sys, 'gettrace', None)

    if gettrace is None:
        return False
    else:
        v = gettrace()
        if v is None:
            return False
        else:
            return True


def build_bins_from_genome(path_to_genome: str,
                           bin_size: int):
    genome = open(path_to_genome, "r")
    nb_bins_per_chr: dict = {}
    for record in FastaIterator(genome):
        chr_id = record.id
        nb_bins_per_chr[chr_id] = len(str(record.seq)) // bin_size + 1
    genome.close()
    total_nb_bins = np.sum(list(nb_bins_per_chr.values()))
    bed_array: dict = {'chr': np.zeros(total_nb_bins, dtype='<U16'),
                       'chr_and_bins': np.zeros(total_nb_bins, dtype='<U64'),
                       'bins_in_chr': np.zeros(total_nb_bins, dtype='<U64'),
                       'bins_in_genome': np.zeros(total_nb_bins, dtype='<U64'),
                       }

    big_counter = 0
    counter = 0
    for ii_chr, nb_bins in nb_bins_per_chr.items():
        for ii_bin in range(0, nb_bins, 1):
            start = ii_bin * bin_size
            bed_array['chr'][counter] = ii_chr
            bed_array['chr_and_bins'][counter] = ii_chr + '_' + str(start)
            bed_array['bins_in_chr'][counter] = start
            bed_array['bins_in_genome'][counter] = start + big_counter * bin_size
            counter += 1
        big_counter += nb_bins
    return bed_array


def frag2(x):
    if x == 'a':
        y = 'b'
    else:
        y = 'a'
    return y


def count_occurrences(df: pd.DataFrame,
                      x: str,
                      contacts_res: dict,
                      infos_res: dict,
                      all_contacted_pos: dict,
                      bin_size):
    y = frag2(x)
    for ii_f, f in enumerate(df['frag_' + x].values):
        if not pd.isna(df['name_' + x][ii_f]):
            if f not in infos_res:
                infos_res[f] = {'type': df['type_' + x][ii_f],
                                'names': [df['name_' + x][ii_f]],
                                'chr': df['chr_' + x][ii_f],
                                'start': df['start_' + x][ii_f],
                                'end': df['end_' + x][ii_f]}

            elif f in infos_res:
                if df['name_' + x][ii_f] not in infos_res[f]['names']:
                    infos_res[f]['names'].append(df['name_' + x][ii_f])

            chr_id = df['chr_' + y][ii_f]
            start = df['start_' + y][ii_f]
            chr_and_pos = chr_id + '_' + str(start)

            if f not in contacts_res:
                contacts_res[f] = {}

            if chr_id not in all_contacted_pos:
                all_contacted_pos[chr_id] = set()

            if chr_and_pos not in all_contacted_pos[chr_id]:
                all_contacted_pos[chr_id].add(start)

            if bin_size > 0:
                start = math.floor(start / bin_size) * bin_size
                bin_id = chr_id + '_' + str(start)
            else:
                bin_id = chr_and_pos

            if bin_id not in contacts_res[f]:
                contacts_res[f][bin_id] = df['contacts'][ii_f]
            else:
                contacts_res[f][bin_id] += df['contacts'][ii_f]

    for f in infos_res:
        if len(infos_res[f]['names']) > 1:
            infos_res[f]['uid'] = '-/-'.join(infos_res[f]['names'])
        else:
            infos_res[f]['uid'] = infos_res[f]['names'][0]

    return contacts_res, infos_res, all_contacted_pos


def get_fragments_dict(contacts_path: str,
                       bin_size: int):
    df_contacts_filtered = pd.read_csv(contacts_path, sep=',')
    fragments_contacts: dict = {}
    fragments_infos: dict = {}
    all_contacted_chr_pos: dict = {}
    fragments_contacts, fragments_infos, all_contacted_chr_pos = \
        count_occurrences(df=df_contacts_filtered,
                          x='a',
                          contacts_res=fragments_contacts,
                          infos_res=fragments_infos,
                          all_contacted_pos=all_contacted_chr_pos,
                          bin_size=bin_size)

    fragments_contacts, fragments_infos, all_contacted_chr_pos = \
        count_occurrences(df=df_contacts_filtered,
                          x='b',
                          contacts_res=fragments_contacts,
                          infos_res=fragments_infos,
                          all_contacted_pos=all_contacted_chr_pos,
                          bin_size=bin_size)

    return fragments_contacts, fragments_infos, all_contacted_chr_pos


def concatenate_infos_and_contacts(df1: pd.DataFrame,
                                   df2: pd.DataFrame,
                                   headers: list):
    df2 = df2.T
    df2.columns = headers
    df3 = pd.concat([df2, df1])
    return df3


def set_fragments_contacts_bins(bed_bins: dict,
                                bins_contacts_dict: dict,
                                fragment_infos_dict: dict,
                                output_path: str):
    chromosomes = bed_bins['chr']
    chr_and_bins = bed_bins['chr_and_bins']
    bins_in_chr = bed_bins['bins_in_chr']
    bins_in_genome = bed_bins['bins_in_genome']
    df_contc = pd.DataFrame({'chr': chromosomes, 'chr_bins': bins_in_chr, 'genome_bins': bins_in_genome})
    df_freq = pd.DataFrame({'chr': chromosomes, 'chr_bins': bins_in_chr, 'genome_bins': bins_in_genome})

    nb_bins = len(bins_in_genome)

    headers = list(df_contc.columns.values)
    fragments = []
    names = ['', '', '']
    types = ['', '', '']
    chrs = ['', '', '']
    starts = ['', '', '']
    ends = ['', '', '']
    for f in bins_contacts_dict:
        contacts = np.zeros(nb_bins, dtype=int)
        fragments.append(f)
        types.append(fragment_infos_dict[f]['type'])
        names.append(fragment_infos_dict[f]['uid'])
        chrs.append(fragment_infos_dict[f]['chr'])
        starts.append(fragment_infos_dict[f]['start'])
        ends.append(fragment_infos_dict[f]['end'])

        for _bin in bins_contacts_dict[f]:
            idx = np.where(chr_and_bins == _bin)[0]
            contacts[idx] = bins_contacts_dict[f][_bin]
        df_contc[f] = contacts
        df_freq[f] = contacts / np.sum(contacts)

    headers.extend(fragments)
    df_infos = pd.DataFrame(
        {'names': names, 'types': types, 'self_chr': chrs, 'self_start': starts, 'self_end': ends})
    df_contc = concatenate_infos_and_contacts(df1=df_contc, df2=df_infos, headers=headers)
    df_freq = concatenate_infos_and_contacts(df1=df_freq, df2=df_infos, headers=headers)
    df_contc.to_csv(output_path + '_contacts_matrix.csv', sep='\t')
    df_freq.to_csv(output_path + '_frequencies_matrix.csv', sep='\t')


def set_fragments_contacts_no_bin(contacts_pos_dict: dict,
                                  fragment_infos_dict: dict,
                                  all_chr_pos: dict,
                                  output_path: str):
    chr_and_pos = []
    chromosomes = []
    positions = []

    for chr_id, pos_list in all_chr_pos.items():
        all_chr_pos[chr_id] = sorted(pos_list)

    chr_unique_list = np.concatenate([['chr' + str(i) for i in range(1, 17)],
                                      ['2_micron', 'mitochondrion', 'chr_artificial']])

    for chr_id in chr_unique_list:
        if chr_id in all_chr_pos:
            new_pos = all_chr_pos[chr_id]
            positions.extend(new_pos)
            chromosomes.extend(np.repeat(chr_id, len(new_pos)))
            for npos in new_pos:
                chr_and_pos.append(chr_id + '_' + str(npos))

    chr_and_pos = np.asarray(chr_and_pos)
    df_contc = pd.DataFrame({'chr': chromosomes, 'positions': positions})
    df_freq = pd.DataFrame({'chr': chromosomes, 'positions': positions})

    headers = list(df_contc.columns.values)
    fragments = []
    names = ['', '']
    types = ['', '']
    chrs = ['', '']
    starts = ['', '']
    ends = ['', '']
    for f in contacts_pos_dict:
        contacts = np.zeros(len(chr_and_pos), dtype=int)
        fragments.append(f)
        types.append(fragment_infos_dict[f]['type'])
        names.append(fragment_infos_dict[f]['uid'])
        chrs.append(fragment_infos_dict[f]['chr'])
        starts.append(fragment_infos_dict[f]['start'])
        ends.append(fragment_infos_dict[f]['end'])

        for pos in contacts_pos_dict[f]:
            idx = np.argwhere(chr_and_pos == pos)[0]
            contacts[idx] = contacts_pos_dict[f][pos]

        df_contc[f] = contacts
        df_freq[f] = contacts / np.sum(contacts)

    headers.extend(fragments)
    df_infos = pd.DataFrame(
        {'names': names, 'types': types, 'self_chr': chrs, 'self_start': starts, 'self_end': ends})
    df_contc = concatenate_infos_and_contacts(df1=df_contc, df2=df_infos, headers=headers)
    df_freq = concatenate_infos_and_contacts(df1=df_freq, df2=df_infos, headers=headers)
    df_contc.to_csv(output_path + '_contacts_matrix.csv', sep='\t')
    df_freq.to_csv(output_path + '_frequencies_matrix.csv', sep='\t')


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        print('Please enter arguments correctly')
        exit(0)

    artificial_genome_path, filtered_contacts_path, output_path, bin_size = ['' for _ in range(4)]

    try:
        opts, args = getopt.getopt(argv, "hg:c:b:o:", ["--help",
                                                       "--genome",
                                                       "--contacts",
                                                       "--bin_size",
                                                       "--output"])
    except getopt.GetoptError:
        print('contacts filter arguments :\n'
              '-g <fasta_genome_input> (artificially generated with oligos_replacement.py) \n'
              '-c <filtered_contacts_input.csv> (contacts filtered with contacts_filter.py) \n'
              '-b <bin_size> (size of a bin, in bp) \n'
              '-o <output_file_name.csv>')
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print('contacts filter arguments :\n'
                  '-g <fasta_genome_input> (artificially generated with oligos_replacement.py) \n'
                  '-c <filtered_contacts_input.csv> (contacts filtered with contacts_filter.py) \n'
                  '-b <bin_size> (size of a bin, in bp) \n'
                  '-o <output_file_name.csv>')
            sys.exit()
        elif opt in ("-g", "--genome"):
            artificial_genome_path = arg
        elif opt in ("-c", "--contacts"):
            filtered_contacts_path = arg
        elif opt in ("-b", "--bin_size"):
            bin_size = arg
        elif opt in ("-o", "--output"):
            output_path = arg.split('.csv')[0]

    bin_size = int(bin_size)
    contacts_dict, infos_dict, all_contacted_pos = get_fragments_dict(contacts_path=filtered_contacts_path,
                                                                      bin_size=bin_size)
    if bin_size > 0:
        bed_pos = build_bins_from_genome(artificial_genome_path, bin_size=bin_size)
        set_fragments_contacts_bins(bed_bins=bed_pos,
                                    bins_contacts_dict=contacts_dict,
                                    fragment_infos_dict=infos_dict,
                                    output_path=output_path)
    else:
        set_fragments_contacts_no_bin(contacts_pos_dict=contacts_dict,
                                      fragment_infos_dict=infos_dict,
                                      all_chr_pos=all_contacted_pos,
                                      output_path=output_path)


def debug(artificial_genome_path: str,
          filtered_contacts_path: str,
          bin_size: int,
          output_path: str):
    contacts_dict, infos_dict, all_contacted_pos = get_fragments_dict(contacts_path=filtered_contacts_path,
                                                                      bin_size=bin_size)
    if bin_size > 0:
        bed_pos = build_bins_from_genome(artificial_genome_path, bin_size=bin_size)
        set_fragments_contacts_bins(bed_bins=bed_pos,
                                    bins_contacts_dict=contacts_dict,
                                    fragment_infos_dict=infos_dict,
                                    output_path=output_path)
    else:
        set_fragments_contacts_no_bin(contacts_pos_dict=contacts_dict,
                                      fragment_infos_dict=infos_dict,
                                      all_chr_pos=all_contacted_pos,
                                      output_path=output_path)


if __name__ == "__main__":
    if is_debug():
        artificial_genome = "../../../bash_scripts/contacts_format/inputs/S288c_DSB_LY_capture_artificial.fa"
        filtered_contacts = "../../../bash_scripts/contacts_format/inputs/contacts_filtered_nicolas.csv"
        output = "../../../bash_scripts/contacts_format/outputs/frequencies_per_bin_matrix.csv"
        bin_size_value = 100000
        debug(artificial_genome_path=artificial_genome,
              filtered_contacts_path=filtered_contacts,
              bin_size=bin_size_value,
              output_path=output)
    else:
        main(sys.argv[1:])

    print('--- DONE ---')
