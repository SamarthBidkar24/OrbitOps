class NeoService:
    def predict(self, date: str, observatory_index: int, app_state):
        """Interface for the NEO risk assessment functionality."""
        neo_module = getattr(app_state, "neo", None)
        if not neo_module:
            raise RuntimeError("NEO prediction module not loaded.")
        
        return neo_module.predict_neo(
            date_str=date, 
            observatory_index=observatory_index
        )

neo_service = NeoService()
