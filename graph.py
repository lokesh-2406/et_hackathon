"""
graph.py — LangGraph orchestration
Wires all 6 agents into a linear pipeline using LangGraph's StateGraph.

Data flow:
  parser → enricher → diagnostician → debate_club → strategist → executor → monitor → END

The shared PortfolioState TypedDict flows through every node.
LangGraph checkpoints state after each node, so a crash mid-pipeline
can be resumed from the last successful agent.
"""
from langgraph.graph import StateGraph, END

from state import PortfolioState
from agents.parser       import run_parser
from agents.enricher     import run_enricher
from agents.diagnostician import run_diagnostician
from agents.debate_club  import run_debate_club
from agents.strategist   import run_strategist
from agents.executor     import run_executor
from agents.monitor      import run_monitor


def build_graph() -> "CompiledGraph":  # type: ignore[name-defined]
    """
    Construct and compile the Portfolio Surgeon LangGraph pipeline.

    All edges are linear (no branching) for reliability during demo.
    Conditional branching (e.g. skip debate if only 1 fund) can be added
    post-hackathon without changing any agent code.

    Returns:
        A compiled LangGraph that can be invoked with an initial state dict.
    """
    g = StateGraph(PortfolioState)

    # Register agent nodes
    g.add_node('parser',       run_parser)
    g.add_node('enricher',     run_enricher)
    g.add_node('diagnostician',run_diagnostician)
    g.add_node('debate_club',  run_debate_club)
    g.add_node('strategist',   run_strategist)
    g.add_node('executor',     run_executor)
    g.add_node('monitor',      run_monitor)

    # Entry point
    g.set_entry_point('parser')

    # Linear pipeline edges
    g.add_edge('parser',        'enricher')
    g.add_edge('enricher',      'diagnostician')
    g.add_edge('diagnostician', 'debate_club')
    g.add_edge('debate_club',   'strategist')
    g.add_edge('strategist',    'executor')
    g.add_edge('executor',      'monitor')
    g.add_edge('monitor',       END)

    return g.compile()


# Module-level singleton — import this in ui/app.py and main.py
portfolio_graph = build_graph()