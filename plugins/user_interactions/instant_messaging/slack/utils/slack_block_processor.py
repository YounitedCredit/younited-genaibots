class SlackBlockProcessor:

    def extract_text_from_blocks(self, blocks):
        if not blocks:
            return ""
            
        text_content = []

        for block in blocks:
            block_type = block.get('type')

            if block_type == 'header' or block_type == 'section':
                text = self.process_header_or_section_block(block)
                if text:
                    text_content.append(text)
            elif block_type == 'context':
                text = self.process_context_block(block)
                if text:
                    text_content.append(text)
            elif block_type == 'rich_text':
                text = self.process_rich_text_block(block)
                if text:
                    text_content.append(text)
            elif block_type == 'input':
                text = self.process_input_block(block)
                if text:
                    text_content.append(text)
            else:
                text_content.append(str(block))

        return ' '.join(text_content).strip()

    def process_header_or_section_block(self, block):
        # Gérer les cas où text est directement un dictionnaire ou est imbriqué
        text_obj = block.get('text', {})
        if isinstance(text_obj, dict):
            # Cas où text est un objet avec type et text
            text = text_obj.get('text', '')
            return text
        elif isinstance(text_obj, str):
            # Cas où text est directement une chaîne
            return text_obj
        return ''

    def process_context_block(self, block):
        text_content = []
        elements = block.get('elements', [])
        
        for element in elements:
            element_type = element.get('type')
            if element_type in ['mrkdwn', 'plain_text']:
                text = element.get('text', '')
                if text:
                    text_content.append(text)
            else:
                # Fallback pour les autres types d'éléments
                text = str(element)
                if text:
                    text_content.append(text)
                    
        return ' '.join(text_content)

    def process_input_block(self, block):
        # Récupérer le texte du label et du placeholder de manière plus robuste
        label_obj = block.get('label', {})
        label = label_obj.get('text', '') if isinstance(label_obj, dict) else str(label_obj)
        
        element = block.get('element', {})
        placeholder_obj = element.get('placeholder', {})
        placeholder = placeholder_obj.get('text', '') if isinstance(placeholder_obj, dict) else str(placeholder_obj)
        
        return f'{label} {placeholder}'.strip()

    def process_rich_text_list(self, element):
        text_content = []
        list_items = element.get('elements', [])
        
        for item in list_items:
            item_type = item.get('type')
            
            if item_type == 'text':
                text = item.get('text', '')
                if text:
                    text_content.append(text)
                    
            elif item_type == 'link':
                url = item.get('url', '')
                text = item.get('text', url)
                text_content.append(f"<{url}|{text}>")
                
            elif item_type == 'user':
                user_id = item.get('user_id', '')
                if user_id:
                    text_content.append(f"<@{user_id}>")
                    
            elif item_type == 'team':
                team_id = item.get('team_id', '')
                if team_id:
                    text_content.append(f"<!subteam^{team_id}>")
                    
            elif item_type == 'channel':
                channel_id = item.get('channel_id', '')
                if channel_id:
                    text_content.append(f"<#{channel_id}>")
                    
            elif item_type == 'emoji':
                name = item.get('name', '')
                if name:
                    text_content.append(f":{name}:")
                    
            elif item_type == 'rich_text_section':
                section_text = self.process_rich_text_list(item)
                if section_text:
                    text_content.append(section_text)
                    
        return ' '.join(text_content)

    def process_rich_text_section_or_preformatted(self, element):
        text_content = []
        sub_elements = element.get('elements', [])
        
        for sub_element in sub_elements:
            if not isinstance(sub_element, dict):
                continue
                
            sub_element_type = sub_element.get('type')
            
            if sub_element_type == 'text':
                text = sub_element.get('text', '')
                if text:
                    text_content.append(text)
                    
            elif sub_element_type == 'link':
                url = sub_element.get('url', '')
                text = sub_element.get('text', url)
                text_content.append(f"<{url}|{text}>")
                
            elif sub_element_type == 'user':
                user_id = sub_element.get('user_id', '')
                if user_id:
                    text_content.append(f"<@{user_id}>")
                    
            elif sub_element_type == 'team':
                team_id = sub_element.get('team_id', '')
                if team_id:
                    text_content.append(f"<!subteam^{team_id}>")
                    
            elif sub_element_type == 'channel':
                channel_id = sub_element.get('channel_id', '')
                if channel_id:
                    text_content.append(f"<#{channel_id}>")
                    
            elif sub_element_type == 'emoji':
                emoji_name = sub_element.get('name', '')
                if emoji_name:
                    text_content.append(f":{emoji_name}:")
                    
            elif sub_element_type == 'broadcast':
                broadcast = sub_element.get('range', '')
                if broadcast:
                    text_content.append(f"<!{broadcast}>")
                    
        return ' '.join(text_content)

    def process_rich_text_block(self, block):
        text_content = []
        elements = block.get('elements', [])
        
        for element in elements:
            element_type = element.get('type')
            
            if element_type == 'rich_text_list':
                list_text = self.process_rich_text_list(element)
                if list_text:
                    text_content.append(list_text)
                    
            elif element_type in ['rich_text_section', 'rich_text_preformatted']:
                section_text = self.process_rich_text_section_or_preformatted(element)
                if section_text:
                    text_content.append(section_text)
                    
        return ' '.join(text_content)