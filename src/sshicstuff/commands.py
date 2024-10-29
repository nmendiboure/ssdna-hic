import os
from docopt import docopt

import sshicstuff.methods as methods
import sshicstuff.log as log
import sshicstuff.pipeline as pip
from sshicstuff.gui.app import app

logger = log.logger


def check_exists(*args):
    """Check if a file exists."""
    for file_path in args:
        if os.path.exists(file_path):
            return
        else:
            logger.error(f"File {file_path} does not exist.")
            raise FileNotFoundError(f"File {file_path} does not exist.")


class AbstractCommand:
    """Base class for the commands"""

    def __init__(self, command_args, global_args):
        """
        Initialize the commands.

        :param command_args: arguments of the command
        :param global_args: arguments of the program
        """
        self.args = docopt(self.__doc__, argv=command_args)
        self.global_args = global_args

    def execute(self):
        """Execute the commands"""
        raise NotImplementedError


class Subsample(AbstractCommand):
    """
    Subsample and compress FASTQ file using seqtk.

    usage:
        subsample -i INPUT [-c] [-F] [-n SIZE] [-s SEED]

    Arguments:
        -i INPUT, --input INPUT   Path to the input original FASTQ file (mandatory)

    options:
        -c, --compress            Compress the output file with gzip [default: True]

        -F, --force               Force the overwriting of the output file if it exists [default: False]

        -n SIZE, --size SIZE      Number of reads to subsample [default: 4000000]

        -s SEED, --seed SEED      Seed for the random number generator [default: 100]

    """
    def execute(self):
        check_exists(self.args["--input"])
        methods.subsample(
            input_path=self.args["--input"],
            seed=int(self.args["--seed"]),
            size=int(self.args["--size"]),
            compress=self.args["--compress"]
        )


class Genomaker(AbstractCommand):
    """
    Create a chromosome artificial that is the concatenation of the annealing oligos and the enzyme sequence.
    Place the newly created chromosome at the end of the genome file.
    Possible to concatenate additional FASTA files to the genome file.
    You can specify the rules for the concatenation.

    usage:
        genomaker -e ENZYME -g GENOME -o OLIGO_ANNEALING [-a ADDITIONAL] [-f FRAGMENT_SIZE] [-l LINE_LENGTH]  [-s SPACER]

    Arguments:
        -e ENZYME, --enzyme ENZYME                                  Sequence of the enzyme

        -g GENOME, --genome GENOME                                  Path to the genome FASTA file

        -o OLIGO_ANNEALING, --oligo-annealing OLIGO_ANNEALING       Path to the annealing oligo positions CSV file (mandatory)

    options:
        -a ADDITIONAL, --additional ADDITIONAL                      Additional FASTA files to concatenate [default: None]

        -f FRAGMENT_SIZE, --fragment-size FRAGMENT_SIZE             Size of the fragments [default: 150]

        -l LINE_LENGTH, --line-length LINE_LENGTH                   Length of the lines in the FASTA file [default: 80]

        -s SPACER, --spacer SPACER                                  Additional FASTA files to concatenate [default: None]
    """

    def execute(self):
        check_exists(self.args["--oligo-annealing"], self.args["--genome"])
        methods.edit_genome_ref(
            self.args["--oligo-annealing"],
            self.args["--genome"],
            self.args["--enzyme"],
            fragment_size=int(self.args["--fragment-size"]),
            fasta_spacer=self.args["--spacer"],
            fasta_line_length=int(self.args["--line-length"]),
            additional_fasta_path=self.args["--additional"]
        )


class Associate(AbstractCommand):
    """
    Simple and basic script to find and associate for each oligo/probe name
    a fragment id from the fragment list generated by hicstuff.

    usage:
        associate -f FRAGMENTS -o OLIGO_CAPTURE [-F]

    Arguments:
        -f FRAGMENTS, --fragments FRAGMENTS                     Path to the fragments file generated by hicstuff (mandatory)

        -o OLIGO_CAPTURE, --oligo-capture OLIGO_CAPTURE         Path to the oligo capture file (mandatory)

    Options:
        -F, --force                                             Force the overwriting of the oligos file even if
                                                                the columns are already present [default: True]
    """

    def execute(self):
        check_exists(self.args["--oligo-capture"], self.args["--fragments"])
        methods.associate_oligo_to_frag(
            oligo_capture_path=self.args["--oligo-capture"],
            fragments_path=self.args["--fragments"],
            force=self.args["--force"]
        )


class Hiconly(AbstractCommand):
    """
    Filter the sparse matrix by removing all the ss DNA specific contacts.
    Retain only the contacts between non-ss DNA fragments.

    usage:
        hiconly -c OLIGOS_CAPTURE -m SPARSE_MATRIX [-o OUTPUT] [-n FLANKING_NUMBER] [-F]

    Arguments:
        -c OLIGOS_CAPTURE, --oligos-capture OLIGOS_CAPTURE      Path to the oligos capture file (mandatory)

        -m SPARSE_MATRIX, --sparse-matrix SPARSE_MATRIX         Path to the sparse matrix file (mandatory)

    Options:
        -o OUTPUT, --output OUTPUT                              Path to the output file

        -n FLANKING_NUMBER, --flanking-number NUMBER            Number of flanking fragments around the fragment
                                                                containing a DSDNA oligo to consider and remove
                                                                [default: 2]

        -F, --force                                             Force the overwriting of the file if
                                                                it exists [default: False]
    """
    def execute(self):
        check_exists(self.args["--sparse-matrix"], self.args["--oligos-capture"])
        methods.hic_only(
            sample_sparse_mat=self.args["--sparse-matrix"],
            oligo_capture_path=self.args["--oligos-capture"],
            output_path=self.args["--output"],
            n_flanking_dsdna=int(self.args["--flanking-number"]),
            force=self.args["--force"]
        )


class Filter(AbstractCommand):
    """
    Filter reads from a sparse matrix and keep only pairs of reads that contain at least one oligo/probe.

    usage:
        filter -f FRAGMENTS -c OLIGOS_CAPTURE -m SPARSE_MATRIX [-o OUTPUT] [-F]

    Arguments:
        -c OLIGOS_CAPTURE, --oligos-capture OLIGOS_CAPTURE      Path to the oligos capture file

        -f FRAGMENTS, --fragments FRAGMENTS                     Path to the digested fragments list file

        -m SPARSE_MATRIX, --sparse-matrix SPARSE_MATRIX         Path to the sparse matrix file

    Options:
        -o OUTPUT, --output OUTPUT                              Path to the output file

        -F, --force                                             Force the overwriting of the file if it exists [default: False]
    """
    def execute(self):
        check_exists(self.args["--fragments"], self.args["--oligos-capture"], self.args["--sparse-matrix"])
        methods.filter_contacts(
            sparse_mat_path=self.args["--sparse-matrix"],
            oligo_capture_path=self.args["--oligos-capture"],
            fragments_list_path=self.args["--fragments"],
            output_path=self.args["--output"],
            force=self.args["--force"]
        )


class Coverage(AbstractCommand):
    """
    Calculate the coverage per fragment and save the result to a bedgraph.

    usage:
        coverage -f FRAGMENTS -m SPARSE_MAT [-o OUTPUT] [-F] [-N]

    Arguments:
        -f FRAGMENTS, --fragments FRAGMENTS       Path to the fragments input file (mandatory)

        -m SPARSE_MAT, --sparse-mat SPARSE_MAT         Path to the sparse contacts input file (mandatory)

    Options:
        -o OUTPUT, --output OUTPUT                          Desired output file path

        -F, --force                                         Force the overwriting of the output file if it exists [default: False]

        -N, --normalize                                     Normalize the coverage by the total number of contacts [default: False]
    """
    def execute(self):
        check_exists(self.args["--fragments"], self.args["--sparse-mat"])
        methods.coverage(
            sparse_mat_path=self.args["--sparse-mat"],
            fragments_list_path=self.args["--fragments"],
            output_path=self.args["--output"],
            normalize=self.args["--normalize"],
            force=self.args["--force"]
        )


class Profile(AbstractCommand):
    """
    Generate oligo 4-C profiles, also known as un-binned tables or 0 kn resolution tables.

    usage:
        profile -c OLIGO_CAPTURE -C CHR_COORD -f FILTERED_TAB  [-o OUTPUT] [-a ADDITIONAL] [-F] [-N]

    Arguments:
        -c OLIGO_CAPTURE, --oligo-capture OLIGOS_CAPTURE       Path to the oligos capture file

        -C CHR_COORD, --chr-coord CHR_COORD                    Path to the chromosome coordinates file

        -f FILTERED_TAB, --filtered-table FILTERED_TAB         Path to the filtered table file

    Options:
        -o OUTPUT, --output OUTPUT                             Desired output file path

        -a ADDITIONAL, --additional ADDITIONAL                 Additional columns to keep in the output file [default: None]

        -F, --force                                            Force the overwriting of the output file if it exists [default: False]

        -N, --normalize                                        Normalize the coverage by the total number of contacts [default: False]
    """
    def execute(self):
        check_exists(self.args["--filtered-table"], self.args["--oligo-capture"], self.args["--chr-coord"])
        methods.profile_contacts(
            filtered_table_path=self.args["--filtered-table"],
            oligo_capture_path=self.args["--oligo-capture"],
            chromosomes_coord_path=self.args["--chr-coord"],
            output_path=self.args["--output"],
            additional_groups_path=self.args["--additional"],
            normalize=self.args["--normalize"],
            force=self.args["--force"]
        )


class Rebin(AbstractCommand):
    """
    Change the binning resolution of a 4C-like profile.

    usage:
        rebin -b BINSIZE -c CHR_COORD -p PROFILE [-o OUTPUT] [-F]

    Arguments:
        -b BINSIZE, --binsize BINSIZE                     New resolution to rebin the profile [default: 1000]

        -c CHR_COORD, --chr-coord CHR_COORD               Path to the chromosome coordinates file

        -p PROFILE, --profile PROFILE                     Path to the profile file (un-binned, 0 kb)

    Options:
        -o OUTPUT, --output OUTPUT                        Desired output file path

        -F, --force                                       Force the overwriting of the output file if it exists [default: False]
    """
    def execute(self):
        check_exists(self.args["--profile"], self.args["--chr-coord"])
        methods.rebin_profile(
            contacts_unbinned_path=self.args["--profile"],
            chromosomes_coord_path=self.args["--chr-coord"],
            bin_size=int(self.args["--binsize"]),
            output_path=self.args["--output"],
            force=self.args["--force"]
        )


class Stats(AbstractCommand):
    """
    Generate statistics about the contacts made by each probe. Additionally, it generates
    the normalized contacts for each probe on each chromosome and on each chromosome except its own.

    It generates 3 outcomes files (.tsv):
    - contacts_statistics.tsv: contains different kinds of statistics for each probe.
    - norm_chr_freq.tsv: contains the normalized contacts for each probe on each chromosome.
    - norm_inter_chr_freq.tsv: contains the normalized contacts for each probe on each chromosome except its own.

    usage:
        stats -c OLIGO_CAPTURE -C CHR_COORD -m SPARSE_MAT -p PROFILE [-o OUTPUT] [-r CIS_RANGE] [-F]

    Arguments:
        -c OLIGO_CAPTURE, --oligo-capture OLIGO_CAPTURE     Path to the oligos capture file

        -C CHR_COORD, --chr-coord CHR_COORD                 Path to the chromosome coordinates file

        -m SPARSE_MAT, --sparse-mat SPARSE_MAT              Path to the sparse contacts input file

        -p PROFILE, --profile PROFILE                       Path to the profile file (un-binned, 0 kb)


    Options:
        -F, --force                                         Force the overwriting of the output file if the file exists [default: False]

        -o OUTPUT, --output OUTPUT                          Desired output directory

        -r CIS_RANGE, --cis-range CIS_RANGE                 Cis range to be considered around the probe [default: 50000]
    """

    def execute(self):
        check_exists(
            self.args["--profile"],
            self.args["--sparse-mat"],
            self.args["--chr-coord"],
            self.args["--oligo-capture"]
        )
        methods.get_stats(
            contacts_unbinned_path=self.args["--profile"],
            sparse_mat_path=self.args["--sparse-mat"],
            chr_coord_path=self.args["--chr-coord"],
            oligo_path=self.args["--oligo-capture"],
            output_dir=self.args["--output"],
            cis_range=int(self.args["--cis-range"]),
            force=self.args["--force"]
        )


class Aggregate(AbstractCommand):
    """
    Aggregate contacts around specific regions of centromeres or telomeres.

    usage:
        aggregate -c OLIGO_CAPTURE -h CHR_COORD -p PROFILE [-o OUTPUT] [-C] [-E CHRS...] [-I] [-L] [-N] [-T] [-w WINDOW]

    Arguments:
        -c OLIGO_CAPTURE, --oligo-capture OLIGO_CAPTURE     Path to the oligo capture CSV file

        -h CHR_COORD, --chr-coord CHR_COORD                 Path to the chromosome coordinates file

        -p PROFILE, --profile PROFILE                       Path to the profile .tsv file with the binning of your choice
                                                            (recommended 1kb for telomeres and 10kb for centromes)
    Options:
        -C, --cen                                           Aggregate only centromeric regions [default: False]

        -E CHRS, --exclude=CHRS                             Exclude the chromosome(s) from the analysis

        -I, --inter                                         Only keep inter-chr contacts, i.e., removing contacts between
                                                            a probe and it own chr [default: True]

        -L, --arm-length                                    Classify telomeres aggregated in according to their arm length.

        -N, --normalize                                     Normalize the contacts by the total number of contacts
                                                            [default: False]

        -o OUTPUT, --output OUTPUT                          Desired output directory

        -T, --tel                                           Aggregate only telomeric regions [default: False]

        -w WINDOW, --window WINDOW                          Window size around the centromere or telomere to aggregate contacts
                                                            [default: 150000]

    """

    def execute(self):
        check_exists(
            self.args["--profile"],
            self.args["--chr-coord"],
            self.args["--oligo-capture"]
        )

        if self.args["--cen"] == self.args["--tel"]:
            logger.error("You must specify either telomeres or centromeres. Not both")
            logger.error("Exiting...")
            raise ValueError("You must specify either telomeres or centromeres. Not both")

        methods.aggregate(
            binned_contacts_path=self.args["--profile"],
            chr_coord_path=self.args["--chr-coord"],
            oligo_capture_path=self.args["--oligo-capture"],
            window_size=int(self.args["--window"]),
            telomeres=self.args["--tel"],
            centromeres=self.args["--cen"],
            output_dir=self.args["--output"],
            excluded_chr_list=self.args["--exclude"],
            inter_only=self.args["--inter"],
            normalize=self.args["--normalize"],
            arm_length_classification=self.args["--arm-length"]
        )


class Compare(AbstractCommand):
    """
    Compare capture efficiency of a sample with a wild-type reference.

    usage:
        compare -s SAMPLE -r REFERENCE -n NAME [-o OUTPUT]

    Arguments:
        -s SAMPLE, --sample-stats SAMPLE            Path to the sample statistics file
                                                    (generated by the stats command)

        -r REFERENCE, --reference-stats REFERENCE   Path to the reference statistics file
                                                    (generated by the stats command)

        -n NAME, --name NAME                        Name of the wt type reference

    Options:
        -o OUTPUT, --output OUTPUT          Desired output directory

    """

    def execute(self):
        check_exists(self.args["--sample-stats"], self.args["--reference-stats"])
        methods.compare_with_wt(
            stats1_path=self.args["--sample-stats"],
            stats2_path=self.args["--reference-stats"],
            ref_name=self.args["--name"],
            output_dir=self.args["--output"]
        )


class View(AbstractCommand):
    """
    Open a graphical user interface to visualize 4-C like profile.

    usage:
        view
    """

    def execute(self):
        app.run_server(debug=True)


class Plot(AbstractCommand):
    """
    Plot a 4-C like profile.

    usage:
        plot -c OLIGO_CAPTURE -C CHR_COORD -p PROFILE [-e EXT] [-h HEIGHT] [-L] [-o OUTDIR]
        [-R REGION] [-r ROLLING_WINDOW] [-w WIDTH] [-y YMIN] [-Y YMAX]

    Arguments:
        -c OLIGO_CAPTURE, --oligo-capture OLIGO_CAPTURE             Path to the oligo capture CSV file (with fragment associated)

        -C CHR_COORD, --chr-coord CHR_COORD                         Path to the chromosome coordinates file

        -p PROFILE, --profile PROFILE                               Path to the profile file (mandatory)


    Options:

        -e EXT, --file-extension EXT                                File extension of the output file (png, pdf, svg, etc.)

        -h HEIGHT, --height HEIGHT                                  Height of the plot (pixels)

        -L, --log                                                   Rescale the y-axis of the plot with np.log

        -o OUTDIR, --output OUTDIR                                  Desired output DIRECTORY

        -R REGION, --region REGION                                  Region to plot (chrN:start-end), start/end in bp
                                                                    Just write chrN: for the whole chromosome

        -r ROLLING_WINDOW, --rolling-window  ROLLING_WINDOW         Apply a rolling window to the profile (convolution size)

        -w WIDTH, --width WIDTH                                     Width of the plot (pixels)

        -y YMIN, --ymin YMIN                                        Minimum value of the y-axis (unit of the Y axis)

        -Y YMAX, --ymax YMAX                                        Maximum value of the y-axis (unit of the Y axis)

    """

    def execute(self):
        check_exists(
            self.args["--profile"],
            self.args["--chr-coord"],
            self.args["--oligo-capture"]
        )

        rolling_window = 1 if not self.args["--rolling-window"] else int(self.args["--rolling-window"])
        methods.plot_profiles(
            profile_contacts_path=self.args["--profile"],
            chr_coord_path=self.args["--chr-coord"],
            oligo_capture_path=self.args["--oligo-capture"],
            output_dir=self.args["--output"],
            extension=self.args["--file-extension"],
            region=self.args["--region"],
            rolling_window=rolling_window,
            log_scale=self.args["--log"],
            user_y_min=self.args["--ymin"],
            user_y_max=self.args["--ymax"],
            width=int(self.args["--width"]),
            height=int(self.args["--height"])
        )


class Pipeline(AbstractCommand):

    """
    Run the entire pipeline containing following steps:
    - Filter
    - HiC only
    - Coverage (full and HiC only)
    - Associate (probe <-> read)
    - Profile
    - Stats
    - Rebin
    - Aggregate (cen & telo)

    usage:
        pipeline -c OLIGO_CAPTURE -C CHR_COORD -f FRAGMENTS -m SPARSE_MATRIX
        [-a ADDITIONAL_GROUPS] [-b BINNING_SIZES...] [-E CHRS...] [-F] [-I] [-L]
        [-n FLANKING_NUMBER] [-N] [-o OUTPUT] [-r CIS_RANGE]
        [--window-size-cen WINDOW_SIZE_CEN] [--window-size-telo WINDOW_SIZE_TELO]
        [--binning-aggregate-cen BIN_CEN] [--binning-aggregate-telo BIN_TELO]
        [--copy-inputs]


    Arguments:
        -c OLIGO_CAPTURE, --oligo-capture OLIGO_CAPTURE     Path to the oligo capture file (.tsv/.csv)

        -C CHR_COORD, --chr-coord CHR_COORD                 Path to the chromosome coordinates file containing
                                                            the chromosome arms length and coordinates of centromeres

        -f FRAGMENTS, --fragments FRAGMENTS                 Path to the digested fragments list file (hicstuff output)

        -m SPARSE_MATRIX, --sparse-matrix SPARSE_MATRIX     Path to the sparse matrix file (hicstuff graal output)

    Options:
        -a ADDITIONAL_GROUPS, --additional-groups ADDITIONAL_GROUPS
                                                            Path to the additional probe groups file

        -b BINNING_SIZES, --binning-sizes BINNING_SIZES     List of binning sizes to rebin the contacts
                                                            [default: 1000]

        -E CHRS, --exclude=CHRS                             Exclude the chromosome(s) from the analysis

        -F, --force                                         Force the overwriting of the output file if it exists
                                                            [default: False]

        -I, --inter                                         Only keep inter-chr contacts, i.e., removing contacts between
                                                            a probe and it own chr [default: True]

        -L, --arm-length                                    Classify telomeres aggregated in according to their arm length.

        -n FLANKING_NUMBER, --flanking-number NUMBER        Number of flanking fragments around the fragment
                                                            containing a DSDNA oligo to consider and remove
                                                            [default: 2]

        -N, --normalize                                     Normalize the coverage by the total number of contacts
                                                            [default: False]

        -o OUTPUT, --output OUTPUT                          Desired output directory

        -r CIS_RANGE, --cis-range CIS_RANGE                 Cis range to be considered around the probe
                                                            [default: 50000]

        --binning-aggregate-cen BIN_CEN                     Binning size of the aggregated profiles to use
                                                            for CENTROMERES

        --binning-aggregate-telo BIN_TELO                   Binning size of the aggregated profiles to use
                                                            for TELOMERES

        --copy-inputs                                       Copy inputs files for reproducibility [default: True]

        --window-size-cen WINDOW_SIZE_CEN                   Window size around the centromeres to aggregate contacts
                                                            [default: 150000]

        --window-size-telo WINDOW_SIZE_TELO                 Window size around the telomeres to aggregate contacts
                                                            [default: 15000]

    """

    def execute(self):
        check_exists(
            self.args["--sparse-matrix"],
            self.args["--oligo-capture"],
            self.args["--fragments"],
            self.args["--chr-coord"]
        )

        binsizes = []
        if self.args["--binning-sizes"]:
            binsizes = [int(b) for b in self.args["--binning-sizes"]]

        pip.full_pipeline(
            sample_sparse_mat=self.args["--sparse-matrix"],
            oligo_capture=self.args["--oligo-capture"],
            fragments_list=self.args["--fragments"],
            chr_coordinates=self.args["--chr-coord"],
            output_dir=self.args["--output"],
            additional_groups=self.args["--additional-groups"],
            bin_sizes=binsizes,
            cen_agg_window_size=int(self.args["--window-size-cen"]),
            cen_aggregated_binning=int(self.args["--binning-aggregate-cen"]),
            telo_agg_window_size=int(self.args["--window-size-telo"]),
            telo_agg_binning=int(self.args["--binning-aggregate-telo"]),
            arm_length_classification=self.args["--arm-length"],
            excluded_chr=self.args["--exclude"],
            cis_region_size=int(self.args["--cis-range"]),
            n_flanking_dsdna=int(self.args["--flanking-number"]),
            inter_chr_only=self.args["--inter"],
            copy_inputs=self.args["--copy-inputs"],
            force=self.args["--force"],
            normalize=self.args["--normalize"]
        )
