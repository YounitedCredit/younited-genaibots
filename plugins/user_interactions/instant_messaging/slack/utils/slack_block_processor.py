class SlackBlockProcessor:
    """
    A processor for extracting text from Slack message blocks.
    """

    def extract_text_from_blocks(self, blocks):
        """
        Extracts text from a list of Slack message blocks.

        Supported block types:
        - 'header' and 'section': Extracts the main text content.
        - 'context': Extracts contextual text from elements.
        - 'rich_text': Processes complex rich text structures.
        - 'input': Extracts labels and placeholders from input fields.
        - Other types: Converts the block to a string representation.

        :param blocks: List of Slack blocks.
        :return: Extracted text content as a string.
        """
        if not blocks:
            return ""
            
        text_content = []

        for block in blocks:
            block_type = block.get('type')

            if block_type in ['header', 'section']:
                text = self.process_header_or_section_block(block)
            elif block_type == 'context':
                text = self.process_context_block(block)
            elif block_type == 'rich_text':
                text = self.process_rich_text_block(block)
            elif block_type == 'input':
                text = self.process_input_block(block)
            else:
                text = str(block)  # Fallback to string conversion for unknown block types
            
            if text:
                text_content.append(text)

        return ' '.join(text_content).strip()

    def process_header_or_section_block(self, block):
        """
        Extracts text from a 'header' or 'section' block.

        The text can be stored directly as a string or as a dictionary containing metadata.

        :param block: Slack block containing a 'text' field.
        :return: Extracted text or an empty string if unavailable.
        """
        text_obj = block.get('text', {})
        if isinstance(text_obj, dict):
            return text_obj.get('text', '')
        return text_obj if isinstance(text_obj, str) else ''

    def process_context_block(self, block):
        """
        Extracts text from a 'context' block, which contains multiple inline elements.

        Supported element types:
        - 'mrkdwn' (Markdown text)
        - 'plain_text' (Plain text)

        :param block: Slack block containing 'elements' list.
        :return: Concatenated text from context elements.
        """
        text_content = []
        elements = block.get('elements', [])
        
        for element in elements:
            element_type = element.get('type')
            if element_type in ['mrkdwn', 'plain_text']:
                text = element.get('text', '')
            else:
                text = str(element)  # Fallback for unknown element types
            
            if text:
                text_content.append(text)
                    
        return ' '.join(text_content)

    def process_input_block(self, block):
        """
        Extracts text from an 'input' block.

        Retrieves both the input label and placeholder if available.

        :param block: Slack block containing an input field.
        :return: Combined label and placeholder text.
        """
        label_obj = block.get('label', {})
        label = label_obj.get('text', '') if isinstance(label_obj, dict) else str(label_obj)
        
        element = block.get('element', {})
        placeholder_obj = element.get('placeholder', {})
        placeholder = placeholder_obj.get('text', '') if isinstance(placeholder_obj, dict) else str(placeholder_obj)
        
        return f'{label} {placeholder}'.strip()

    def process_rich_text_list(self, element):
        """
        Processes a 'rich_text_list' element, extracting text from each list item.

        Supported sub-elements:
        - 'text': Extracts raw text.
        - 'link': Formats URLs as Slack-style links.
        - 'user': Extracts user mentions.
        - 'team': Extracts team mentions.
        - 'channel': Extracts channel references.
        - 'emoji': Extracts emoji notation.
        - 'rich_text_section': Recursively processes nested sections.

        :param element: Rich text list element.
        :return: Concatenated extracted text.
        """
        text_content = []
        list_items = element.get('elements', [])
        
        for item in list_items:
            item_type = item.get('type')
            
            if item_type == 'text':
                text = item.get('text', '')
            elif item_type == 'link':
                url = item.get('url', '')
                text = item.get('text', url)
                text = f"<{url}|{text}>"
            elif item_type == 'user':
                text = f"<@{item.get('user_id', '')}>"
            elif item_type == 'team':
                text = f"<!subteam^{item.get('team_id', '')}>"
            elif item_type == 'channel':
                text = f"<#{item.get('channel_id', '')}>"
            elif item_type == 'emoji':
                text = f":{item.get('name', '')}:"
            elif item_type == 'rich_text_section':
                text = self.process_rich_text_list(item)  # Recursive processing
            else:
                text = ""

            if text:
                text_content.append(text)
                    
        return ' '.join(text_content)

    def process_rich_text_section_or_preformatted(self, element):
        """
        Extracts text from a 'rich_text_section' or 'rich_text_preformatted' element.

        Handles various element types such as text, links, user mentions, team mentions, and emojis.

        :param element: Slack rich text section or preformatted block.
        :return: Concatenated extracted text.
        """
        text_content = []
        sub_elements = element.get('elements', [])
        
        for sub_element in sub_elements:
            if not isinstance(sub_element, dict):
                continue
                
            sub_element_type = sub_element.get('type')
            
            if sub_element_type == 'text':
                text = sub_element.get('text', '')
            elif sub_element_type == 'link':
                url = sub_element.get('url', '')
                text = sub_element.get('text', url)
                text = f"<{url}|{text}>"
            elif sub_element_type == 'user':
                text = f"<@{sub_element.get('user_id', '')}>"
            elif sub_element_type == 'team':
                text = f"<!subteam^{sub_element.get('team_id', '')}>"
            elif sub_element_type == 'channel':
                text = f"<#{sub_element.get('channel_id', '')}>"
            elif sub_element_type == 'emoji':
                text = f":{sub_element.get('name', '')}:"
            elif sub_element_type == 'broadcast':
                text = f"<!{sub_element.get('range', '')}>"
            else:
                text = ""

            if text:
                text_content.append(text)
                    
        return ' '.join(text_content)

    def process_rich_text_block(self, block):
        """
        Extracts text from a 'rich_text' block.

        Processes nested rich text elements, including lists and sections.

        :param block: Slack block containing rich text elements.
        :return: Concatenated extracted text.
        """
        text_content = []
        elements = block.get('elements', [])
        
        for element in elements:
            element_type = element.get('type')
            
            if element_type == 'rich_text_list':
                text = self.process_rich_text_list(element)
            elif element_type in ['rich_text_section', 'rich_text_preformatted']:
                text = self.process_rich_text_section_or_preformatted(element)
            else:
                text = ""

            if text:
                text_content.append(text)
                    
        return ' '.join(text_content)
