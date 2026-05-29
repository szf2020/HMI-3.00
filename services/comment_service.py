# services\comment_service.py
import logging

logger = logging.getLogger(__name__)

class CommentService:
    """
    A service class to manage data for all comment tables in a project.
    This acts as a centralized in-memory store for comment spreadsheet data.
    """
    def __init__(self):
        self._comments_data = {}

    def load_data(self, data):
        """Loads all comment data from a project file."""
        self._comments_data = data if isinstance(data, dict) else {}

    def get_all_data(self):
        """Returns all comment data for saving to a project file."""
        return self._comments_data

    def get_comment(self, comment_number):
        """Gets the full comment object (metadata and table data)."""
        return self._comments_data.get(str(comment_number))

    def get_table_data(self, comment_number):
        """
        Retrieves the spreadsheet data for a specific comment table.
        Returns a list of lists representing rows and columns.
        """
        comment = self.get_comment(comment_number)
        return comment.get('table_data', []) if comment else []

    def update_table_data(self, comment_number, table_data):
        """
        Updates the spreadsheet data for a specific comment table.
        `table_data` should be a list of lists.
        """
        comment_number_str = str(comment_number)
        if comment_number_str in self._comments_data:
            self._comments_data[comment_number_str]['table_data'] = table_data
        else:
            self._comments_data[comment_number_str] = {'metadata': {'number': comment_number}, 'table_data': table_data}

    def add_comment(self, comment_metadata):
        """Adds a new comment with its metadata and an empty table."""
        number = comment_metadata.get('number')
        if number is None:
            return
        number_str = str(number)
        if number_str not in self._comments_data:
            self._comments_data[number_str] = {
                'metadata': comment_metadata,
                'table_data': []  # Initialize with empty data
            }
            self._comments_data[number_str].update(comment_metadata)

    def remove_comment(self, comment_number):
        """Removes a comment from the service."""
        comment_number_str = str(comment_number)
        if comment_number_str in self._comments_data:
            del self._comments_data[comment_number_str]

    def update_comment_metadata(self, comment_metadata):
        """Updates the metadata (like name or description) of a comment."""
        number = comment_metadata.get('number')
        if number is None:
            return
        number_str = str(number)
        if number_str in self._comments_data:
            self._comments_data[number_str]['metadata'] = comment_metadata
            for key, value in comment_metadata.items():
                self._comments_data[number_str][key] = value

    def clear_data(self):
        """Clears all comment data, used when creating a new project."""
        self._comments_data = {}
