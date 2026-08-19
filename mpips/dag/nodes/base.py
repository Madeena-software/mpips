from typing import Any, Dict


class BaseNode:
    """Base class for all image processing DAG nodes."""

    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the node logic.

        Args:
            inputs: Dict mapping input slot names to values
                (typically numpy arrays or numbers).
            params: Dict mapping parameter names to values (from catalog schemas).

        Returns:
            Dict mapping output slot names to computed values.
        """
        raise NotImplementedError("Subclasses must implement the execute method.")
