from __future__ import absolute_import, division, print_function, unicode_literals
import os
import json
import argparse
import numpy as np
import multiprocessing as mp
from AdaptivePELE.utilities import utilities
import AdaptivePELE.atomset.atomset as atomset
from AdaptivePELE.analysis import analysis_utils


def parseArguments():
    """
        Parse the command-line options

        :returns: object -- Object containing the options passed
    """
    desc = "Program that fixes RMSD symmetries of a PELE report file."\
           "Control file is a JSON file that contains \"resname\", \"native\", "\
           "symmetries, and, optionally, the column to substitute in report. "\
           "Example of content:"\
           "{"\
           "\"resname\" : \"K5Y\","\
           "\"native\" : \"native.pdb\","\
           "\"symmetries\" : [{\"4122:C12:K5Y\":\"4123:C13:K5Y\", \"4120:C10:K5Y\":\"4127:C17:K5Y\"}],"\
           "\"column\" = 5"\
           "}"
    parser = argparse.ArgumentParser(description=desc)
    parser.add_argument("controlFile", type=str, help="Control File name")
    parser.add_argument("--report_name", type=str, default=None, help="Name of report files, for example if reports are named 'report_1' use report")
    parser.add_argument("--trajectory_name", type=str, default=None, help="Name of trajectory files, for example if reports are named 'run_trajectories_1' use run_trajectories")
    parser.add_argument("--path", type=str, default=".", help="Path where the simulation is stored")
    parser.add_argument("--top", type=str, default=None, help="Topology file for non-pdb trajectories or path to Adaptive topology object")
    parser.add_argument("--out_name", type=str, default="fixedReport", help="Name of the modified report files (default is fixedReport)")
    parser.add_argument("--out_folder", type=str, default=None, help="Path where to store the report files (default is fixedReport)")
    parser.add_argument("-n", type=int, default=1, help="Number of processors to parallelize")
    parser.add_argument("--fmt_str", type=str, default="%.4f", help="Format of the output file (default is .4f which means all floats with 4 decimal points)")
    args = parser.parse_args()

    return args.controlFile, args.report_name, args.trajectory_name, args.path, args.top, args.out_name, args.n, args.out_folder, args.fmt_str


def readControlFile(controlFile):
    """
        Extract parameters from controlFile

        :param controlFile: Control file
        :type controlFile: str
        :returns: str, str, list, int -- Name of the ligand in the pdb, filename
            containing the native structure, list of the symmetry groups, column
            corresponding to the rmsd in the report file
    """
    jsonFile = open(controlFile, 'r').read()
    parsedJSON = json.loads(jsonFile)
    resname = parsedJSON["resname"]
    nativeFilename = parsedJSON["native"]
    symmetries = parsedJSON["symmetries"]
    rmsdColInReport = parsedJSON.get("column")
    if not rmsdColInReport:
        # append to the end
        rmsdColInReport = -1

    return resname, nativeFilename, symmetries, rmsdColInReport


def calculate_rmsd_traj(nativePDB, resname, symmetries, rmsdColInReport, traj, reportName, top, epoch, outputFilename, fmt_str):
    top_proc = None
    if top is not None:
        top_proc = utilities.getTopologyFile(top)
    rmsds = utilities.getRMSD(traj, nativePDB, resname, symmetries, topology=top_proc)

    with open(reportName) as f:
        header = f.readline().rstrip()
        if not header.startswith("#"):
            header = ""
        reportFile = utilities.loadtxtfile(reportName)
    if rmsdColInReport > 0 and rmsdColInReport < reportFile.shape[1]:
        reportFile[:, rmsdColInReport] = rmsds
        fixedReport = reportFile
    else:
        fixedReport = analysis_utils.extendReportWithRmsd(reportFile, rmsds)

    with open(outputFilename, "w") as fw:
        if header:
            fw.write("%s\tRMSD\n" % header)
        else:
            fw.write("# Step\tRMSD\n")
        np.savetxt(fw, fixedReport, fmt=fmt_str)


def main(controlFile, trajName, reportName, folder, top, outputFilename, nProcessors, output_folder, format_str):
    """
        Calculate the corrected rmsd values of conformation taking into account
        molecule symmetries

        :param controlFile: Control file
        :type controlFile: str
        :param folder: Path the simulation
        :type folder: str
        :param top: Path to the topology
        :type top: str
        :param outputFilename: Name of the output file
        :type outputFilename: str
        :param nProcessors: Number of processors to use
        :type nProcessors: int
        :param output_folder: Path where to store the new reports
        :type output_folder: str
        :param format_str: String with the format of the report
        :type format_str: str
    """
    if trajName is None:
        trajName = "*traj*"
    else:
        trajName += "_*"
    if reportName is None:
        reportName = "*report_%d"
    else:
        reportName += "_%d"
    if output_folder is not None:
        outputFilename = os.path.join(output_folder, outputFilename)
    outputFilename += "_%d"
    if nProcessors is None:
        nProcessors = utilities.getCpuCount()
    nProcessors = max(1, nProcessors)
    print("Calculating RMSDs with %d processors" % nProcessors)
    pool = mp.Pool(nProcessors)
    epochs = utilities.get_epoch_folders(folder)
    if top is not None:
        top_obj = utilities.getTopologyObject(top)
    else:
        top_obj = None

    resname, nativeFilename, symmetries, rmsdColInReport = readControlFile(controlFile)

    nativePDB = atomset.PDB()
    nativePDB.initialise(nativeFilename, resname=resname)

    files = []
    if not epochs:
        # path does not contain an adaptive simulation, we'll try to retrieve
        # trajectories from the specified path
        files = analysis_utils.process_folder(None, folder, trajName, reportName, os.path.join(folder, outputFilename), top_obj)
    for epoch in epochs:
        print("Epoch", epoch)
        files.extend(analysis_utils.process_folder(epoch, folder, trajName, reportName, os.path.join(folder, epoch, outputFilename), top_obj))
    results = []
    for info in files:
        results.append(pool.apply_async(calculate_rmsd_traj, args=(nativePDB, resname, symmetries, rmsdColInReport, info[0], info[1], info[2], info[3], info[4], format_str)))
    for res in results:
        res.get()
    pool.close()
    pool.terminate()


if __name__ == "__main__":
    control_file, name_report, name_traj, path, topology_path, out_name, n_proc, out_folder, fmt = parseArguments()
    main(control_file, name_traj, name_report, path, topology_path, out_name, n_proc, out_folder, fmt)
