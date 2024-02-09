import os
import sys
import argparse
import pandas as pd
import numpy as np
from utils import frag2


def starts_match(fragments: pd.DataFrame, oligos: pd.DataFrame) -> pd.DataFrame:
    """
    Update the start positions of the oligos DataFrame based on the corresponding fragment positions.

    If the capture oligo is inside a fragment, update the start position of the oligos DataFrame with the start
    position of the fragment.

    Parameters
    ----------
    fragments : pd.DataFrame
        The fragments DataFrame.
    oligos : pd.DataFrame
        The oligos DataFrame.

    Returns
    -------
    pd.DataFrame
        The updated oligos DataFrame.
    """
    l_starts = []
    for i in range(len(oligos)):
        oligos_chr = oligos['chr'][i]
        middle = int((oligos['end'][i] - oligos['start'][i] - 1) / 2 + oligos['start'][i] - 1)
        if oligos_chr == 'chr_artificial':
            for k in reversed(range(len(fragments))):
                interval = range(fragments['start'][k], fragments['end'][k])
                fragments_chr = fragments['chr'][k]
                if middle in interval and fragments_chr == oligos_chr:
                    l_starts.append(fragments['start'][k])
                    break
        else:
            for k in range(len(fragments)):
                interval = range(fragments['start'][k], fragments['end'][k] + 1)
                fragments_chr = fragments['chr'][k]

                if middle in interval and fragments_chr == oligos_chr:
                    l_starts.append(fragments['start'][k])
                    break
    oligos['start'] = list(l_starts)
    return oligos


def oligos_fragments_joining(fragments: pd.DataFrame, oligos: pd.DataFrame) -> pd.DataFrame:
    """
    Join the oligos and fragments DataFrames, removing fragments that do not contain an oligo region.

    Updates the start and end columns with the corresponding fragment positions.

    Parameters
    ----------
    fragments : pd.DataFrame
        The fragments DataFrame.
    oligos : pd.DataFrame
        The oligos DataFrame.

    Returns
    -------
    pd.DataFrame
        The joined oligos and fragments DataFrame.
    """
    oligos = starts_match(fragments, oligos)
    oligos.set_index(['chr', 'start'])
    oligos.pop("end")
    fragments.set_index(['chr', 'start'])
    oligos_fragments = fragments.merge(oligos, on=['chr', 'start'])
    oligos_fragments.sort_values(by=['chr', 'start'])
    return oligos_fragments


def first_join(x: str, oligos_fragments: pd.DataFrame, contacts: pd.DataFrame) -> pd.DataFrame:
    """
    Join the contacts and oligos_fragments DataFrames, keeping only the rows that have their 'x' fragment
    (either 'frag_a' or 'frag_b', see contacts_correction function).

    Parameters
    ----------
    x : str
        Either 'a' or 'b', indicating whether to join on 'frag_a' or 'frag_b'.
    oligos_fragments : pd.DataFrame
        The joined oligos and fragments DataFrame.
    contacts : pd.DataFrame
        The corrected contacts DataFrame.

    Returns
    -------
    pd.DataFrame
        The joined contacts and oligos_fragments DataFrame.
    """

    joined = contacts.merge(oligos_fragments, left_on='frag_'+x, right_on='frag', how='inner')
    return joined


def second_join(
        x: str, fragments: pd.DataFrame, oligos_fragments: pd.DataFrame, contacts: pd.DataFrame) -> pd.DataFrame:
    """
    Add the fragments DataFrame information (=columns) for the y fragment after the first join
    (see first_join function). This is only for the y fragment, because the x fragments already have their
    information in the oligos_fragments DataFrame.

    Parameters
    ----------
    x : str
        Either 'a' or 'b', indicating which fragment corresponds to an oligo.
    fragments : pd.DataFrame
        The corrected fragments DataFrame.
    oligos_fragments : pd.DataFrame
        The joined oligos and fragments DataFrame.
    contacts : pd.DataFrame
        The corrected contacts DataFrame.

    Returns
    -------
    pd.DataFrame
        The joined DataFrame with added fragment information for the y fragment.
    """
    new_contacts = first_join(x, oligos_fragments, contacts)
    y = frag2(x)
    joined = new_contacts.join(fragments.drop("frag", axis=1),
                               on='frag_'+y,
                               lsuffix='_' + x[-1],
                               rsuffix='_' + y[-1], how='left')

    # puts a suffix to know what fragment corresponds to an oligo
    joined.rename(columns={"type": "type_" + x[-1],
                           "name": "name_" + x[-1],
                           "sequence": "sequence_" + x[-1]
                           },
                  inplace=True)
    return joined


def filter_contacts(oligos_path: str, fragments_path: str, contacts_path: str, output_dir: str) -> None:
    """

    """
    sample_name = contacts_path.split("/")[-1].split(".")[0]

    """
    Fragment import and correction of col names
    """

    df_fragments_raw = pd.read_csv(fragments_path, sep='\t')
    df_fragments = pd.DataFrame(
        {'frag': [k for k in range(len(df_fragments_raw))],
         'chr': df_fragments_raw['chrom'],
         'start': df_fragments_raw['start_pos'],
         'end': df_fragments_raw['end_pos'],
         'size': df_fragments_raw['size'],
         'gc_content': df_fragments_raw['gc_content']
         }
    )

    """
    Oligos import and addition of fragment information (fragment containing the oligo)
    """

    df_oligos = pd.read_csv(oligos_path, sep=",")
    if "fragment" not in df_oligos.columns:
        fragments_id = []
        fragments_start = []
        fragments_end = []

        for index, row in df_oligos.iterrows():
            chr_, probe_start, probe_end, probe_type, probe, probe_seq = row
            df_sub_fragments = df_fragments[df_fragments['chr'] == chr_]
            df_sub_fragment_sorted_start = np.sort(df_sub_fragments['start'].to_numpy())

            probe_middle = int(probe_start + (probe_end-probe_start)/2)

            idx = np.searchsorted(df_sub_fragment_sorted_start, probe_middle, side="left")
            nearest_frag_start = df_sub_fragment_sorted_start[idx-1]

            frag_id = df_sub_fragments.index[df_sub_fragments['start'] == nearest_frag_start].tolist()[0]
            frag_start = df_sub_fragments.loc[frag_id, 'start']
            frag_end = df_sub_fragments.loc[frag_id, 'end']
            fragments_id.append(frag_id)
            fragments_start.append(frag_start)
            fragments_end.append(frag_end)

        df_oligos.insert(5, "fragment", np.array(fragments_id))
        df_oligos.insert(6, "fragment_start", np.array(fragments_start))
        df_oligos.insert(7, "fragment_end", np.array(fragments_end))

    df_oligos.to_csv(oligos_path, sep=",", index=False)

    """
    Contacts import and correction of col names
    """

    df_contacts_raw = pd.read_csv(contacts_path, sep='\t', header=None)
    df_contacts = df_contacts_raw.drop([0])
    df_contacts.reset_index(drop=True, inplace=True)
    df_contacts.columns = ['frag_a', 'frag_b', 'contacts']

    """
    Joining of the 3 dataframes
    """

    df_oligos_fragments = oligos_fragments_joining(df_fragments, df_oligos)
    df1 = second_join('a', df_fragments, df_oligos_fragments, df_contacts)
    df2 = second_join('b', df_fragments, df_oligos_fragments, df_contacts)
    df_contacts_joined = pd.concat([df1, df2])
    df_contacts_joined.drop("frag", axis=1, inplace=True)
    df_contacts_joined.sort_values(by=['frag_a', 'frag_b', 'start_a', 'start_b'], inplace=True)
    df_contacts_filtered = df_contacts_joined.convert_dtypes().reset_index(drop=True)

    output_path_filtered: str = os.path.join(output_dir, "contacts_filtered.tsv")
    df_contacts_filtered.to_csv(output_path_filtered, sep='\t', index=False)

    """
    Create a contacts file with the same format as the input file, but with the filtered contacts (no ssDNA)
    """

    # foi : fragments of interest
    df_foi = pd.DataFrame(df_oligos['fragment'].unique(), columns=['fragments'])
    df_contacts_hic_only = df_contacts_raw.copy(deep=True)

    df_contacts_raw["index"] = df_contacts_raw.index
    matches_a = pd.merge(df_contacts_raw, df_foi, left_on=0, right_on='fragments', how='inner', indicator=True)
    matches_b = pd.merge(df_contacts_raw, df_foi, left_on=1, right_on='fragments', how='inner', indicator=True)
    index_to_drop = np.unique(np.concatenate((matches_a['index'].to_numpy(), matches_b['index'].to_numpy())))

    df_contacts_hic_only.drop(index_to_drop, inplace=True)

    df_contacts_hic_only.iloc[0, 0] -= len(df_foi)
    df_contacts_hic_only.iloc[0, 1] -= len(df_foi)
    df_contacts_hic_only.iloc[0, 2] -= len(index_to_drop)

    output_path_hic_only: str = os.path.join(output_dir, f"{sample_name}_hic.txt")
    df_contacts_hic_only.to_csv(output_path_hic_only, sep='\t', index=False, header=False)


def main(argv=None):
    """
    Main function to run the filter_contacts script.

    Parses command line arguments and calls the filter_contacts function.

    Parameters
    ----------
    argv : list of str, optional
        List of command line arguments, by default None.

    Returns
    -------
    None
    """

    #   Example :
    """
    -f ../test_data/AD162_classic/fragments_list.txt 
    -c ../test_data/AD162_classic/AD162/AD162_S288c_DSB_LY_Capture_artificial_cutsite_q30.txt 
    -o ../test_data/AD162_classic/AD162/
    --oligos ../test_data/AD162_classic/capture_oligo_positions.csv 
    """

    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        print('Please enter arguments correctly')
        exit(0)

    parser = argparse.ArgumentParser(description='Contacts filter arguments')

    parser.add_argument('-f', '--fragments', type=str, required=True,
                        help='Path to the fragments_input.txt file (generated by hicstuff)')
    parser.add_argument('-c', '--contacts', type=str, required=True,
                        help='Path to the sparse_contacts_input.txt file (generated by hicstuff)')
    parser.add_argument('--oligos', type=str, required=True,
                        help='Path to the oligos_input.csv file')
    parser.add_argument('-o', '--output-dir', type=str, required=True,
                        help='Path to the output directory')

    args = parser.parse_args(argv)
    filter_contacts(args.oligos, args.fragments, args.contacts, args.output_dir)


if __name__ == "__main__":
    main(sys.argv[1:])