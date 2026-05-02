# intelligence/pipeline.py (SIMPLIFIÉ - SAFE WRAPPER)

from intelligence.user_intelligence_engine import get_user_intelligence

def run_user_intelligence(user_email, profile=None, portfolio=None, conn=None):
    """
    Wrapper compatible legacy (NE CASSE PAS LES ROUTES EXISTANTES)
    """

    return get_user_intelligence(user_email)
