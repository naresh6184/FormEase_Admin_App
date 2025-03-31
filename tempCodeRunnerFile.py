def handle_editor_closed(self, editor, hint):
        if self.last_edited_item:
            self.last_edited_item.setFlags(self.last_edited_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.last_edited_item = None