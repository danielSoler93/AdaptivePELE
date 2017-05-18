import time
import sys
import os
import numpy as np
import networkx as nx
from AdaptivePELE.clustering import clustering, thresholdcalculator
from AdaptivePELE.spawning import spawning, densitycalculator


def getUnvisitedPath(clustering, numClusters=5):
    conf = clustering.conformationNetwork
    visited = set()
    path = []
    stack = [0]
    while stack:
        node = stack.pop(0)
        path.append(node)
        visited.add(node)
        minVisit = 1e6
        minNeigh = None
        for foo, target, data in conf.out_edges_iter(node, data=True):
            if data['transition'] < minVisit and target not in visited:
                minVisit = data['transition']
                minNeigh = target
        if minNeigh is not None:
            stack.append(minNeigh)

    if len(path) <= numClusters:
        return path
    else:
        return path[-1:-numClusters-1:-1]

def getShortestPath(clustering, numClusters=5):
    conf = clustering.conformationNetwork
    contacts = [cluster.contacts for cluster in clustering.clusterIterator()]
    maxCluster = np.argmax(contacts)
    shortPath = nx.shortest_path(conf, source=0, target=maxCluster, weight='transition')
    if len(shortPath) <= numClusters:
        return shortPath
    else:
        return shortPath[-1:-numClusters-1:-1]

def getMetastableClusters(clustering, numClusters=5):
    betweenness = nx.betweenness_centrality(clustering.conformationNetwork, weight='transition')
    conf = clustering.conformationNetwork
    b2 = np.array([betweenness[i] for i in xrange(len(betweenness))])
    thresholds = [cluster.threshold for cluster in clustering.clusters.clusters]
    metInd = np.zeros_like(thresholds, dtype=np.float)
    for node in conf.nodes_iter():
        if conf.degree(node) < 1:
            metInd[node] = 0.0
            continue
        totalIn = 0
        totalOut = 0
        selfTrans = 0
        totalKin = 0
        for source, foo, data in conf.in_edges_iter(node, data=True):
            if source != node:
                totalIn += data['transition']*thresholds[source]**3
        for n, edge, data in conf.out_edges_iter(node, data=True):
            if edge == node:
                selfTrans = data['transition']
            totalOut += data['transition']*thresholds[edge]**3
            totalKin += data['transition']
        if totalOut+selfTrans:
            metInd[node] = (totalIn/float(totalOut))*(selfTrans/float(totalKin))
        else:
            metInd[node] = 0.0
    finalMetInd = metInd*b2
    return np.argsort(finalMetInd)[-1:-numClusters-1:-1]

def getMetastableClusters2(clustering, numClusters=5):
    betweenness = nx.betweenness_centrality(clustering.conformationNetwork, weight='transition')
    b2 = np.array([betweenness[i] for i in xrange(len(betweenness))])
    return np.argsort(b2)[-1:-numClusters-1:-1]

def getMetastableClusters5(clustering, numClusters=5):
    conf = clustering.conformationNetwork
    thresholds = [cluster.threshold for cluster in clustering.clusters.clusters]
    minThres = min(thresholds)
    volume = np.zeros(len(thresholds))
    for node in conf.nodes_iter():
        vol = 0.0
        for foo, target in conf.edges_iter(node):
            assert foo == node
            cluster = clustering.getCluster(target)
            vol += (cluster.threshold/minThres)**3
        volume[node] = vol
    return np.argsort(volume)[:numClusters+1]

def getMetastableClusters4(clustering, numClusters=5):
    conf = clustering.conformationNetwork
    metrics = [cluster.getMetricFromColumn(4) for cluster in clustering.clusters.clusters]
    indexes = np.zeros_like(metrics)
    outInd = np.zeros_like(metrics)
    inInd = np.zeros_like(metrics)
    with open("informationNetwork.csv", "w") as f:
        f.write("Node\tthreshold\tinDegree\toutDegree\tDegree\n")
        for node in conf.nodes_iter():
            outNeigh = 0.0
            inNeigh = 0.0
            countOut = 0
            countIn = 0
            for foo, target in conf.out_edges_iter(node):
                cluster = clustering.getCluster(target)
                countOut += 1
                outNeigh += (cluster.elements/cluster.threshold**3-outNeigh)/float(countOut)

            for source, foo in conf.in_edges_iter(node):
                cluster = clustering.getCluster(source)
                countIn += 1
                inNeigh += (cluster.elements/cluster.threshold**3-inNeigh)/float(countIn)
            outInd[node] = outNeigh
            inInd[node] = inNeigh
            if inNeigh > 1e-8:
                indexes[node] = outNeigh/inNeigh
            else:
                indexes[node] = 0.0
    return np.argsort(indexes)[-1:-numClusters-1:-1]


def getMetastableClusters3(clustering, numClusters=5):
    betweenness = nx.betweenness_centrality(clustering.conformationNetwork, weight='transition')
    conf = clustering.conformationNetwork
    thresholds = [cluster.threshold for cluster in clustering.clusters.clusters]
    metInd = np.zeros_like(thresholds, dtype=np.float)
    for node in conf.nodes_iter():
        if conf.degree(node) < 1:
            metInd[node] = 0.0
            continue
        totalIn = 0
        totalOut = 0
        selfTrans = 0
        totalKin = 0
        for source, foo, data in conf.in_edges_iter(node, data=True):
            if source != node:
                totalIn += data['transition']*thresholds[source]**3
        for n, edge, data in conf.out_edges_iter(node, data=True):
            if edge == node:
                selfTrans = data['transition']
            totalOut += data['transition']*thresholds[edge]**3
            totalKin += data['transition']
        if totalOut+selfTrans:
            metInd[node] = (totalIn/float(totalOut))*(selfTrans/float(totalKin))
        else:
            metInd[node] = 0.0
    finalMetInd = metInd
    return np.argsort(finalMetInd)[-1:-numClusters-1:-1]

nclusters = 80
thresholdCalculatorBuilder = thresholdcalculator.ThresholdCalculatorBuilder()
thresholdCalculator = thresholdCalculatorBuilder.build({
        "thresholdCalculator": {
            "type": "heaviside",
            "params": {
                "values": [2, 3, 4, 5],
                "conditions": [1, 0.75, 0.5]
            }
        }
})
# thresholdCalculator = thresholdCalculatorBuilder.build({})
# Distance index
# similarityEvaluator = clustering.differenceDistanceEvaluator()
# thresholdCalculatorAcc = thresholdCalculatorBuilder.build({
#     "thresholdCalculator": {
#         "type": "heaviside",
#         "params": {
#             "conditions": [1.2, 1.0, 0.5, 0.0],
#             "values": [0.2, 0.4, 0.5, 0.8]
#         }
#     }
# })
# Jaccard index
similarityEvaluator = clustering.JaccardEvaluator()
# thresholdCalculatorAcc = thresholdCalculatorBuilder.build({
#     "thresholdCalculator": {
#         "type" : "heaviside",
#         "params" : {
#             "conditions" : [1, 0.75, 0.5],
#             "values" : [0.025, 0.03, 0.04, 0.05]
#         }
#     }
# })
thresholdCalculatorAcc = thresholdCalculatorBuilder.build({
    "thresholdCalculator": {
        "type" : "heaviside",
        "params" : {
            "values" : [0.2, 0.3, 0.5, 0.8],
            "conditions" : [1.0, 0.75, 0.5]
        }
    }
})
# correlation
# similarityEvaluator = clustering.correlationEvaluator()
# thresholdCalculatorAcc = thresholdCalculatorBuilder.build({
#     "thresholdCalculator": {
#         "type": "constant",
#         "params": {
#             "value": 0.15
#         }
#     }
# })
densityCalculatorBuilder = densitycalculator.DensityCalculatorBuilder()
# densityCalculator = densityCalculatorBuilder.build({
#        "density": {
#             "type": "heaviside",
#             "params": {
#                  "conditions": [1.5, 1.0, 0.0],
#                  "values": [8.0, 2.37, 1.0, 0.5]
#              }
#         }
#    }
# )
# densityCalculator = densityCalculatorBuilder.build({})
densityCalculator = densityCalculatorBuilder.build({
    "density": {
        "type": "continuous"
    }
})
spawnParams = spawning.SpawningParams()
spawnParams.buildSpawningParameters({
    "type": "epsilon",
    "params": {
        "epsilon": 0.0,
        "T": 1000,
        "reportFilename": "report",
        "metricColumnInReport": 5
        }
    })
contactThresholdDistance = 8
resname = "DAJ"
nEpochs = 21
altSel = False
ntrajs = 32
ClCont = clustering.ContactsClustering(thresholdCalculator, resname=resname,
                                       reportBaseFilename="report",
                                       columnOfReportFile=6,
                                       contactThresholdDistance=contactThresholdDistance,
                                       symmetries=[], altSelection=altSel)
ClAcc = clustering.ContactMapAccumulativeClustering(thresholdCalculatorAcc,
                                                    similarityEvaluator,
                                                    resname=resname,
                                                    reportBaseFilename="report",
                                                    columnOfReportFile=4,
                                                    contactThresholdDistance=contactThresholdDistance,
                                                    altSelection=altSel)
# spawningObject = spawning.InverselyProportionalToPopulationCalculator(densityCalculator)
# spawningObject = spawning.UCBCalculator(densityCalculator)
spawningObject = spawning.EpsilonDegeneracyCalculator(densityCalculator)
# ClAcc.clusterInitialStructures(["/home/jgilaber/PR/PR_prog_initial_adaptive.pdb"])
ClCont.clusterInitialStructures(["/home/jgilaber/4DAJ/4DAJ_initial_adaptive.pdb"])
processorMapping = [0 for i in xrange(ntrajs-1)]
if not os.path.exists("mappings"):
    os.makedirs("mappings")
if not os.path.exists("results"):
    os.makedirs("results")
# fw = open("clusters.txt", "w")
# fw2 = open("clustersBet.txt", "w")
# fw3 = open("clustersInd.txt", "w")
# fw4 = open("clustersIndNew.txt", "w")
# fw5 = open("clustersVol.txt", "w")
# fw6 = open("clustersVisit.txt", "w")
for i in range(nEpochs):
    # path =["trajs/%d/run_traj*"%i]
    # paths_report = ["trajs/%d/run_report*"%i]
    # path = ["/home/bsc72/bsc72021/simulations/PR/testCM_4_32/simulation/PRprog_CM_variabExtra_UCB_5/%d/traj*" % i]
    # paths_report = ["/home/bsc72/bsc72021/simulations/PR/testCM_4_32/simulation/PRprog_CM_variabExtra_UCB_5//%d/report*" % i]
    # path = ["/gpfs/scratch/bsc72/bsc72021/AdaptiveCM/simulation/PRprog_4_64CMExtraSubset_prova_SASA3/%d/traj*"%i]
    # paths_report = ["/gpfs/scratch/bsc72/bsc72021/AdaptiveCM/simulation/PRprog_4_64CMExtraSubset_prova_SASA3/%d/report*"%i]
    # path = ["/home/jgilaber/PR/PR_simulation_network/%d/traj*"%i]
    # paths_report = ["/home/jgilaber/PR/PR_simulation_network/%d/report*"%i]
    path = ["/home/jgilaber/4DAJ/4DAJ_4_32/%d/traj*"%i]
    paths_report = ["/home/jgilaber/4DAJ/4DAJ_4_32/%d/report*"%i]
    trajs = clustering.getAllTrajectories(paths_report)
    total_snapshots = 0
    for traj in trajs:
        for line in open(traj, "r"):
            total_snapshots += 1
        total_snapshots -= 1
    sys.stderr.write("Total snapsthots for epoch %d: %d\n" % (i, total_snapshots))
    startTimeCont = time.time()
    ClCont.cluster(path, processorMapping)
    endTimeCont = time.time()
    sys.stderr.write("Total time of clustering contacts, epoch %d: %.6f\n"%(i,endTimeCont-startTimeCont))
    sys.stderr.write("Number of clusters contacts epoch %d: %d\n"%(i,len(ClCont.clusters.clusters)))
    degeneraciesCont = spawningObject.calculate(ClCont.clusters.clusters, ntrajs-1, spawnParams)
    nProc = 0
    clusterList = processorMapping[:]
    for icl in xrange(len(ClCont.clusters.clusters)):
        for j in range(int(degeneraciesCont[icl])):
            clusterList[nProc] = icl
            nProc += 1
    assert nProc == ntrajs-1
    processorMapping = clusterList[1:]+[clusterList[0]]
    with open("mappings/mapping%d.txt"%i, "w") as f:
        f.write(','.join(map(str, processorMapping)))
    ClCont.writeOutput("clsummary",degeneraciesCont,"ClCont.pkl", False)
    os.rename("clsummary/summary.txt", "results/summary_ClCont.txt")
    # sortedNodes = getMetastableClusters(ClCont, 10)
    # sortedNodes = set(sortedNodes)
    # print sortedNodes
    # for node in sortedNodes:
    #     cluster = ClCont.getCluster(node)
    #     fw.write("%d\t%.3f\n" % (i*4, cluster.getMetricFromColumn(4)))

    # startTimeAcc = time.time()
    # ClAcc.cluster(path, processorMapping)
    # endTimeAcc = time.time()
    # sys.stderr.write("Total time of clustering accumulative, epoch %d: %.6f\n" % (i,endTimeAcc-startTimeAcc))
    # sys.stderr.write("Number of clusters accumulative epoch %d: %d\n" % (i,len(ClAcc.clusters.clusters)))
    # degeneraciesAcc = spawningObject.calculate(ClAcc.clusters.clusters, ntrajs-1, spawnParams)
    # # summaryFolder = "%d/clustering" % i
    # # if not os.path.exists(summaryFolder):
    # #     os.makedirs(summaryFolder)
    # nProc = 0
    # clusterList = processorMapping[:]
    # for icl in xrange(len(ClAcc.clusters.clusters)):
    #     for j in range(int(degeneraciesAcc[icl])):
    #         clusterList[nProc] = icl
    #         nProc += 1
    # assert nProc == ntrajs-1
    # ClAcc.writeOutput("clsummary", degeneraciesAcc, "ClAcc.pkl", False)
    # os.rename("clsummary/summary.txt", "results/summary_ClAcc.txt")
    # processorMapping = clusterList[1:]+[clusterList[0]]
    # with open("mappings/mapping%d.txt" % i, "w") as f:
    #     f.write(','.join(map(str, processorMapping)))
    # # sortedNodes = getMetastableClusters(ClAcc, 10)
    # # sortedNodes = set(sortedNodes)
    # # sortedNodes2 = getMetastableClusters2(ClAcc, 10)
    # # sortedNodes2 = set(sortedNodes2)
    # # sortedNodes3 = getMetastableClusters3(ClAcc, 10)
    # # sortedNodes3 = set(sortedNodes3)
    # # sortedNodes4 = getMetastableClusters4(ClAcc, 10)
    # # sortedNodes4 = set(sortedNodes4)
    # # sortedNodes5 = getMetastableClusters5(ClAcc, 10)
    # # sortedNodes5 = set(sortedNodes5)
    # # print sortedNodes
    # # print sortedNodes2
    # # print sortedNodes3
    # # print sortedNodes4
    # # print sortedNodes5
    # # for node in sortedNodes:
    # #     cluster = ClAcc.getCluster(node)
    # #     fw.write("%d\t%.3f\n" % ((i+1)*4, cluster.originalMetrics[4]))
    # # for node in sortedNodes2:
    # #     cluster = ClAcc.getCluster(node)
    # #     fw2.write("%d\t%.3f\n" % ((i+1)*4, cluster.originalMetrics[4]))
    # # for node in sortedNodes3:
    # #     cluster = ClAcc.getCluster(node)
    # #     fw3.write("%d\t%.3f\n" % ((i+1)*4, cluster.originalMetrics[4]))
    # # for node in sortedNodes4:
    # #     cluster = ClAcc.getCluster(node)
    # #     fw4.write("%d\t%.3f\n" % ((i+1)*4, cluster.originalMetrics[4]))
    # # for node in sortedNodes5:
    # #     cluster = ClAcc.getCluster(node)
    # #     fw5.write("%d\t%.3f\n" % ((i+1)*4, cluster.originalMetrics[4]))
    # # path = getUnvisitedPath(ClAcc, 10)
    # path = getShortestPath(ClAcc, 10)
    # print path
    # for node in path:
    #     cluster = ClAcc.getCluster(node)
    #     fw6.write("%d\t%.3f\n" % ((i+1)*4, cluster.originalMetrics[4]))