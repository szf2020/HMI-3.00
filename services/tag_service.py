# services\tag_service.py
import logging

logger = logging.getLogger(__name__)


class TagService:
    """
    A service class to manage data for all tag tables in a project.
    This acts as a centralized in-memory store for tag data,
    similar to CommentService for comments.
    """

    def __init__(self, project_service=None):
        self._tags_data = {}
        self.project_service = project_service

    def set_project_service(self, project_service):
        """Attach the project service used for immediate JSON synchronization."""
        self.project_service = project_service

    def _sync_tag(self, tag_number):
        if self.project_service is None:
            return
        tag = self.get_tag(tag_number)
        if tag is not None:
            self.project_service.sync_tag(tag_number, tag)

    def load_data(self, data):
        """Loads all tag data from a project file without writing it back to disk."""
        self._tags_data = data if isinstance(data, dict) else {}

    def get_all_data(self):
        """Returns all tag data for saving to a project file."""
        return self._tags_data

    def get_tag(self, tag_number):
        """Gets the full tag object (metadata and table data)."""
        return self._tags_data.get(str(tag_number))

    def get_table_data(self, tag_number):
        """
        Retrieves the table data for a specific tag.
        Returns a list representing tag rows.
        """
        tag = self.get_tag(tag_number)
        return tag.get('table_data', tag.get('tags', [])) if tag else []

    def update_table_data(self, tag_number, table_data):
        """
        Updates the table data for a specific tag and immediately syncs it to disk.
        `table_data` should be a list of tag row data.
        """
        tag_number_str = str(tag_number)
        if tag_number_str in self._tags_data:
            self._tags_data[tag_number_str]['table_data'] = table_data
            self._tags_data[tag_number_str]['tags'] = table_data
        else:
            self._tags_data[tag_number_str] = {
                'metadata': {'number': tag_number},
                'number': tag_number,
                'table_data': table_data,
                'tags': table_data,
            }
        self._sync_tag(tag_number_str)

    def add_tag(self, tag_metadata):
        """Adds a new tag with its metadata and an empty table, then syncs it to disk."""
        number = tag_metadata.get('number')
        if number is None:
            return
        number_str = str(number)
        if number_str not in self._tags_data:
            tag_payload = {
                'metadata': tag_metadata,
                'table_data': tag_metadata.get('table_data', tag_metadata.get('tags', [])),
                'tags': tag_metadata.get('tags', tag_metadata.get('table_data', [])),
            }
            # Also store the original metadata fields at root level for compatibility.
            tag_payload.update(tag_metadata)
            self._tags_data[number_str] = tag_payload
        self._sync_tag(number_str)

    def remove_tag(self, tag_number):
        """Removes a tag from the service and immediately deletes its JSON file."""
        tag_number_str = str(tag_number)
        if tag_number_str in self._tags_data:
            del self._tags_data[tag_number_str]
        if self.project_service is not None:
            self.project_service.delete_tag(tag_number_str)

    def update_tag_metadata(self, tag_metadata):
        """Updates the metadata (like name or description) of a tag and syncs it to disk."""
        number = tag_metadata.get('number')
        if number is None:
            return
        number_str = str(number)
        if number_str in self._tags_data:
            existing_table_data = self._tags_data[number_str].get(
                'table_data', self._tags_data[number_str].get('tags', [])
            )
            self._tags_data[number_str]['metadata'] = tag_metadata
            self._tags_data[number_str]['table_data'] = existing_table_data
            self._tags_data[number_str]['tags'] = existing_table_data
            # Also update root level fields for compatibility.
            for key, value in tag_metadata.items():
                self._tags_data[number_str][key] = value
        else:
            self.add_tag(tag_metadata)
            return
        self._sync_tag(number_str)

    def get_tag_numbers(self):
        """Returns a list of all tag numbers."""
        return [int(k) for k in self._tags_data.keys()]

    def tag_exists(self, tag_number):
        """Checks if a tag with the given number exists."""
        return str(tag_number) in self._tags_data

    def clear_data(self):
        """Clears all tag data, used when creating a new project."""
        self._tags_data = {}
