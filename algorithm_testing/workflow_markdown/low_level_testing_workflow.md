flowchart TB

%% --------------------------
%% Benchmark: produces metrics DataFrame
%% --------------------------
subgraph Benchmark[Algorithm Benchmark Flow]
    B_Start["Start benchmark run"]

    %% Configurations & Scenarios
    B_Configs["Define algorithm CONFIGS (bnb_dijkstra, bnb_astar, runtime_repeats)"]
    B_Scenarios["Define SCENARIOS (graph_path, entry, items, checkouts)"]

    %% Quality Benchmark: run_experiments()
    B_RunExp["run_experiments() over all (scenario × algorithm)"]
    B_LoadGraph["Load GraphML and ensure each edge has a 'weight' attribute"]
    B_Eval["evaluate_all_criteria() → runtime_seconds, distance, turns, route (order, walk)"]
    B_Row["Build metrics row for each setup = scenario__algorithm"]
    B_DF["Benchmark DataFrame (indexed by setup)"]


    %% Main flow: Quality Benchmark
    B_Start --> B_Configs
    B_Configs --> B_Scenarios
    B_Scenarios --> B_RunExp
    B_RunExp --> B_LoadGraph
    B_LoadGraph --> B_Eval
    B_Eval --> B_Row
    B_Row --> B_DF


end

%% --------------------------
%% Criteria Diagrams
%% --------------------------
subgraph CriteriaDiagrams[Criteria Diagrams Flow]
    C_Start["Start criteria_diagrams main()"]

    %% Input & raw export
    C_InDF["Take benchmark DataFrame (one row per setup)"]
    C_RawCSV["Save criteria_raw_metrics_per_setup.csv (full metrics per setup)"]

    %% Aggregation per algorithm
    C_Agg["Group by algorithm_setup and compute mean(runtime_seconds, distance, turns)"]
    C_AggCSV["Save criteria_metrics_per_algorithm.csv (aggregated per algorithm)"]

    %% Visualization
    C_CategoryLoop["Iterate over categories: distance, turns, runtime_seconds"]
    C_Plot["Generate bar chart PNG for each category (absolute values per algorithm)"]
end

%% Connect Benchmark → Criteria Diagrams
B_DF --> C_InDF
C_Start --> C_InDF
C_InDF --> C_RawCSV
C_InDF --> C_Agg
C_Agg --> C_AggCSV
C_AggCSV --> C_CategoryLoop --> C_Plot

%% --------------------------
%% Heatmap (full workflow: normalize, aggregate, visualize)
%% --------------------------
subgraph Heatmap[Heatmap Flow]
    H_Start["Start heatmap main()"]

    %% Input
    H_InDF["Take benchmark DataFrame (distance, turns, runtime_seconds per setup)"]

    %% Step 1: Scenario-specific normalization
    H_GroupScenario["Group rows by scenario"]
    H_NormMetrics["Within each scenario: min–max normalize distance/turns/runtime_seconds to 0–100 (invert: smaller is better)"]
    H_OverallIndex["Compute overall_score per setup (mean of normalized metrics)"]
    H_PerSetup["Assemble per_setup_index: scenario, algorithm, normalized metrics, overall_score"]

    %% Step 2: Aggregate across scenarios
    H_PerAlgo["Group per_setup_index by algorithm_setup and average normalized scores → per_algorithm_index"]

    %% Step 3: Export & Visualization
    H_SetupCSV["Save per_setup_index → heatmap_index_per_setup.csv"]
    H_AlgoCSV["Save per_algorithm_index → heatmap_index_per_algorithm.csv"]
    H_SavePNG["Render per_algorithm_index as heatmap_index_per_algorithm.png (rows = algorithms, columns = categories)"]
end

%% Connect Benchmark → Heatmap
B_DF --> H_InDF
H_Start --> H_InDF
H_InDF --> H_GroupScenario
H_GroupScenario --> H_NormMetrics --> H_OverallIndex --> H_PerSetup
H_PerSetup --> H_PerAlgo
H_PerSetup --> H_SetupCSV
H_PerAlgo --> H_AlgoCSV --> H_SavePNG