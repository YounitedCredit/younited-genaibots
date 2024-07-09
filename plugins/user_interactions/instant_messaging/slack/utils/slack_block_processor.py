class SlackBlockProcessor:

    def extract_text_from_blocks(self, blocks):
        text_content = []

        for block in blocks:
            block_type = block.get('type')

            if block_type == 'header' or block_type == 'section':
                text_content.append(self.process_header_or_section_block(block))
            elif block_type == 'context':
                text_content.append(self.process_context_block(block))
            elif block_type == 'rich_text':
                text_content.append(self.process_rich_text_block(block))
            elif block_type == 'input':
                text_content.append(self.process_input_block(block))
            else:
                text_content.append(str(block))

        return ' '.join(text_content).strip()

    def process_header_or_section_block(self, block):
        return block.get('text', {}).get('text', '')

    def process_context_block(self, block):
        text_content = []
        elements = block.get('elements', [])
        for element in elements:
            if element.get('type') == 'mrkdwn' or element.get('type') == 'plain_text':
                text_content.append(element.get('text', ''))
        return ' '.join(text_content)

    def process_input_block(self, block):
        label = block.get('label', {}).get('text', '')
        placeholder = block.get('element', {}).get('placeholder', {}).get('text', '')
        return f'{label} {placeholder}'

    def process_rich_text_list(self, element):
        text_content = []
        list_items = element.get('elements', [])
        for item in list_items:
            item_type = item.get('type')
            if item_type == 'text':
                text_content.append(item.get('text', ''))
            elif item_type == 'link':
                url = item.get('url', '')
                text = item.get('text', url)  # Use the URL as the default text if no text is provided
                text_content.append(f"<{url}|{text}>")
            elif item_type == 'user':
                user_id = item.get('user_id', '')
                text_content.append(f"User Mention: <@{user_id}>")
            elif item_type == 'team':
                team_id = item.get('team_id', '')
                text_content.append(f"Team Mention: <!subteam^{team_id}>")
            elif item_type == 'channel':
                channel_id = item.get('channel_id', '')
                text_content.append(f"Channel Mention: <#{channel_id}>")
            elif item_type == 'emoji':
                name = item.get('name', '')
                text_content.append(f":{name}:")
            elif item_type == 'rich_text_section':
                text_content.append(self.process_rich_text_list(item))
        return ' '.join(text_content)

    def process_rich_text_section_or_preformatted(self, element):
        text_content = []
        sub_elements = element.get('elements', [])
        for sub_element in sub_elements:
            sub_element_type = sub_element.get('type')
            if sub_element_type == 'text':
                text_content.append(sub_element.get('text', ''))
            elif sub_element_type == 'link':
                url = sub_element.get('url', '')
                text = sub_element.get('text', url)  # Use the URL as the default text if no text is provided
                text_content.append(f"<{url}|{text}>")
            elif sub_element_type == 'user':
                user_id = sub_element.get('user_id', '')
                text_content.append(f"User Mention: <@{user_id}>")
            elif sub_element_type == 'team':
                team_id = sub_element.get('team_id', '')
                text_content.append(f"Team Mention: <!subteam^{team_id}>")
            elif sub_element_type == 'channel':
                channel_id = sub_element.get('channel_id', '')
                text_content.append(f"Channel Mention: <#{channel_id}>")
            elif sub_element_type == 'emoji':
                emoji_name = sub_element.get('name', '')
                text_content.append(f":{emoji_name}:")
            elif sub_element_type == 'broadcast':
                broadcast = sub_element.get('range', '')
                text_content.append(f"Broadcast: <{broadcast}>")
        return ' '.join(text_content)

    def process_rich_text_block(self, block):
        text_content = []
        elements = block.get('elements', [])
        for element in elements:
            element_type = element.get('type')
            if element_type == 'rich_text_list':
                text_content.append(self.process_rich_text_list(element))
            elif element_type in ['rich_text_section', 'rich_text_preformatted']:
                text_content.append(self.process_rich_text_section_or_preformatted(element))
        return ' '.join(text_content)
