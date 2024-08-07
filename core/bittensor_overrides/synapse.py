import base64
import json
import sys
from typing import Any, ClassVar, Dict


import bittensor
from bittensor import Synapse as bt_Synapse


class Synapse(bt_Synapse):
    _model_json_schema: ClassVar[Dict[str, Any]]

    @classmethod
    def _get_cached_model_json_schema(cls) -> dict:
        """
        Returns the JSON schema for the Synapse model.
        This method returns a cached version of the JSON schema for the Synapse model.
        The schema is stored in the class variable ``_model_json_schema`` and is only
        generated once to improve performance.
        Returns:
            dict: The JSON schema for the Synapse model.
        """
        if "_model_json_schema" not in cls.__dict__:
            cls._model_json_schema = cls.model_json_schema()
        return cls._model_json_schema

    def get_required_fields(self):
        """
        Get the required fields from the model's JSON schema.
        """
        schema = self._get_cached_model_json_schema()
        return schema.get("required", [])

    def to_headers(self) -> dict:
        """
        Converts the state of a Synapse instance into a dictionary of HTTP headers.

        This method is essential for
        packaging Synapse data for network transmission in the Bittensor framework, ensuring that each key aspect of
        the Synapse is represented in a format suitable for HTTP communication.

        Process:

        1. Basic Information: It starts by including the ``name`` and ``timeout`` of the Synapse, which are fundamental for identifying the query and managing its lifespan on the network.
        2. Complex Objects: The method serializes the ``axon`` and ``dendrite`` objects, if present, into strings. This serialization is crucial for preserving the state and structure of these objects over the network.
        3. Encoding: Non-optional complex objects are serialized and encoded in base64, making them safe for HTTP transport.
        4. Size Metrics: The method calculates and adds the size of headers and the total object size, providing valuable information for network bandwidth management.

        Example Usage::

            synapse = Synapse(name="ExampleSynapse", timeout=30)
            headers = synapse.to_headers()
            # headers now contains a dictionary representing the Synapse instance

        Returns:
            dict: A dictionary containing key-value pairs representing the Synapse's properties, suitable for HTTP communication.
        """
        # Initializing headers with 'name' and 'timeout'
        headers = {"name": self.name, "timeout": str(self.timeout)}

        # Adding headers for 'axon' and 'dendrite' if they are not None
        if self.axon:
            headers.update({f"bt_header_axon_{k}": str(v) for k, v in self.axon.model_dump().items() if v is not None})
        if self.dendrite:
            headers.update(
                {f"bt_header_dendrite_{k}": str(v) for k, v in self.dendrite.model_dump().items() if v is not None}
            )

        # Getting the fields of the instance
        instance_fields = self.model_dump()

        required = set(self.get_required_fields())
        # Iterating over the fields of the instance
        for field, value in instance_fields.items():
            # If the object is not optional, serializing it, encoding it, and adding it to the headers
            # Skipping the field if it's already in the headers or its value is None
            if field in headers or value is None:
                continue

            elif field in required:
                try:
                    # create an empty (dummy) instance of type(value) to pass pydantic validation on the axon side
                    serialized_value = json.dumps(value.__class__.__call__())
                    encoded_value = base64.b64encode(serialized_value.encode()).decode("utf-8")
                    headers[f"bt_header_input_obj_{field}"] = encoded_value
                except TypeError as e:
                    raise ValueError(
                        f"Error serializing {field} with value {value}. Objects must be json serializable."
                    ) from e

        # Adding the size of the headers and the total size to the headers
        headers["header_size"] = str(sys.getsizeof(headers))
        headers["total_size"] = str(self.get_total_size())
        headers["computed_body_hash"] = self.body_hash

        return headers
