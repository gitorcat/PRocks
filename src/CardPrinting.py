
import numpy as np
import cv2
import json
from urllib.request import urlopen

'''
Methods for printing custom Magic: the Gathering cards.
'''

class CardPrinter:

    def __init__(self):

        # Asset path stems
        self.face_path_stem = ".\\Assets\\Faces\\"
        self.font_path_stem = ".\\Assets\\Fonts\\"

        # Pixel overlay calibrations
        self.mc_xoffset = 650
        self.mc_yoffset = 8
        self.name_xoffset = 20
        self.name_yoffset = 12
        self.stats_xoffset = 632
        self.stats_yoffset = 904
        self.type_xoffset = 34
        self.type_yoffset = 550
        self.rarity_xoffset = 577
        self.rarity_yoffset = 540
        self.illus_xoffset = 333
        self.illus_yoffset = 912
        self.ability_xoffset = 58
        self.ability_yoffset = 744
        self.max_ability_width = 538
        self.max_ability_length = 270

        # Special string printing characters
        self.special_characters  = ["Space", ".", ",", "'", "\"", ":", ";", "+", "-", "=", "_", "*", "~", "^", "`", "|", "/", "&", "?", "!", "$", "@", "#", "%", "<", ">", "(", ")"]

    def read_nalpha_image(self, image_nalpha_path):
        '''
        Reads image with no transparency and removes all (pure) green pixels

        Args:
            image_nalpha_path: Image path

        Returns:
            Image with transparency
        '''

        # Read image with no transparency
        image_nalpha = cv2.imread(image_nalpha_path)

        # Add alpha channel
        image = cv2.cvtColor(image_nalpha, cv2.COLOR_BGR2BGRA)
        
        # Define green screen range
        lower_green = np.array([0, 255, 0])
        upper_green = np.array([0, 255, 0])

        # Create mask to identify green pixels
        mask = cv2.inRange(image_nalpha, lower_green, upper_green)
        
        # Set alpha channel to 0 for specified pixels
        image[mask > 0, 3] = 0

        return image
        
    def overlay_sprite(self, background, sprite, x_offset, y_offset):
        '''
        Overlays a sprite image (with transparency) onto a background image

        Args:
            background: Background image
            sprite: Sprite image
            x_offset: Horizontal offset (pixels) from the top-left corner of the background image
            y_offset: Vertical offset (pixels) from the top-left corner of the background image

        Returns:
            The background image overlayed with the sprite image
        '''

        # Get sprite dimensions
        sprite_height, sprite_width = sprite.shape[:2]

        # Extract alpha channel from sprite, normalized to [0,1]
        alpha = sprite[:, :, 3] / 255.0

        # Extract BGR channels from sprite
        sprite_bgr = sprite[:, :, :3]

        # Calculate region of interest in background image where sprite will be placed
        roi = background[y_offset:y_offset + sprite_height, x_offset:x_offset + sprite_width]

        # Blend sprite onto region of interest using alpha channel
        for c in range(0, 3):
            roi[:, :, c] = (alpha * sprite_bgr[:, :, c] + (1 - alpha) * roi[:, :, c])

        # Update background image with modified region of interest
        background[y_offset:y_offset + sprite_height, x_offset:x_offset + sprite_width] = roi

        return background

    def define_character_path(self, character, font):
        '''
        Gathers image path information for specific character

        Args:
            character: Input charcter string
            font: Character font

        Returns:
            Character image path
        '''

        # Uppercase letter
        if character.isupper():
            character_path = self.font_path_stem + font + "\\Letters\\" + character + "\\0.png"
            new_character = True
        # Lowercase letter
        elif character.islower():
            character_path = self.font_path_stem + font + "\\Letters\\" + character + "\\1.png"
            new_character = True
        # Number
        elif character.isdigit():
            character_path = self.font_path_stem + font + "\\Digits\\" + character + ".png"
            new_character = True
        # Known special character
        elif character in self.special_characters:
            character_path = self.font_path_stem + font + "\\Special\\" + str(self.special_characters.index(character)) + ".png"
            new_character = True
        # Unknown special character
        else:
            character_path = self.font_path_stem + font + "\\Special\\0.png"

        return character_path

    def generate_string_image(self, string, font):
        '''
        Creates image of given string

        Args:
            string: Input string
            font: Character font

        Returns:
            String image
        '''
        
        # Initiate blank image
        start_plate_path = self.font_path_stem + font + "\\Special\\0.png"
        image = self.read_nalpha_image(start_plate_path)
        
        # Read character paths
        for character in string:

            # Known character path
            character_path = self.define_character_path(character, font)
            new_image = self.read_nalpha_image(character_path)
            image = cv2.hconcat([image, new_image])

        return image

    def write_mana_cost(self, mana_cost):
        '''
        Determines card color and creates mana cost image

        Args:
            mana_cost: Mana cost symbols list

        Returns:
            Mana cost image and card color
        '''
        
        # Initialize as colorless
        color = "Artifact"
        colored = False
        multicolored = False

        # Empty mana cost image
        mana_cost_stem = self.read_nalpha_image(self.font_path_stem + "Name\\Symbols\\manacoststem.png")
        mana_cost_image = mana_cost_stem

        # Land, no mana cost symbols
        if not mana_cost:
            color = "Nonbasic"

        # Print mana cost symbols
        else:

            # Read mana cost symbol and add to mana cost image
            for symbol in mana_cost:
                symbol_path = self.font_path_stem + "Name\\Symbols\\" + str(symbol) + ".png"
                symbol_image = self.read_nalpha_image(symbol_path)
                mana_cost_image = cv2.hconcat([mana_cost_image, symbol_image])
                mana_cost_image = cv2.hconcat([mana_cost_image, mana_cost_stem])

                # Color introduced to mana cost
                if not isinstance(symbol, int) and symbol != "X":

                    # Ignore symbols of same color
                    if not colored:
                        first_color = symbol
                        color = symbol
                        colored = True

                    # Multiple colors introduced to mana cost
                    elif not multicolored and symbol != first_color:
                        multicolored = True
                        color = "Multicolor" 

        return color, mana_cost_image

    def write_ability(self, ability_strings, max_line_width, max_lines):
        '''
        Creates single card ability image

        Args:
            ability_strings: List of ability line strings
            max_line_width: Maximum pixel width of ability image
            max_lines: Maximum number of ability line strings

        Returns:
            Mana cost image and card color
        '''

        # Define ability error space
        space_path = self.font_path_stem + "Ability\\Special\\0.png"
        space = self.read_nalpha_image(space_path)
        ability_plate_path = self.font_path_stem + "Ability\\ability_line_plate.png"
        ability_line_plate = self.read_nalpha_image(ability_plate_path)
        ability_space_path = self.font_path_stem + "Ability\\ability_line_space.png"
        ability_line_space = self.read_nalpha_image(ability_space_path)
        first_line = True
        lines = []

        # Read input strings
        for ability_string in ability_strings:
            words = ability_string.split()
            first_word = True
            first_quote = True
            italics = False
            symbol = False
            font = "Ability\\"

            # Create word images
            for word in words:
                first_character = True
                symbol_string = ""
                
                # Gather individual character images
                for character in word:
                    print_character = False

                    # Start italics
                    if character == "[":
                        font = "Flavor\\"
                    # End italics
                    elif character == "]":
                        font = "Ability\\"

                    # Start symbol
                    elif character == "{":
                        symbol = True
                    # End symbol
                    elif character == "}":
                        character_path = self.font_path_stem + font + "Symbols\\" + symbol_string + ".png"
                        print_character = True
                        symbol = False
                    # Read symbol
                    elif symbol:
                        symbol_string += character

                    elif character == "\"":
                        if first_quote:
                            first_quote = False
                        else:
                            first_quote = True
                            character = "`"
                        character_path = self.define_character_path(character, font)
                        print_character = True

                    # Read character
                    else:
                        character_path = self.define_character_path(character, font)
                        print_character = True

                    # Start word image
                    if first_character and print_character:
                        word_image = self.read_nalpha_image(character_path)
                        first_character = False
                    # Continue word image
                    elif print_character:
                        character_image = self.read_nalpha_image(character_path)
                        word_image = cv2.hconcat([word_image, character_image])

                # Start line image
                if first_word:
                    line_image = word_image
                    first_word = False
                # End line image
                elif np.shape(line_image)[1] + np.shape(space)[1] + np.shape(word_image)[1] > self.max_ability_width:
                    lines.append(line_image)
                    line_image = word_image
                # Continue line image
                else:
                    line_image = cv2.hconcat([line_image, space])
                    line_image = cv2.hconcat([line_image, word_image])

            # Continue line images list
            lines.append(line_image)
            lines.append(ability_line_space)

        # Reset first line count
        first_line = True

        # Create ability image
        for ability_line in lines[0:-1]:
            ability_plate_extension = ability_line_plate[0:np.shape(ability_line)[0], 0:(self.max_ability_width - np.shape(ability_line)[1]), :]
            ability_line = cv2.hconcat([ability_line, ability_plate_extension])

            # Count first line
            if first_line:
                ability_image = ability_line
                first_line = False
            # Continue ability image
            else:
                ability_image = cv2.vconcat([ability_image, ability_line])

        return ability_image

    def print_card(self, card_data):
        '''
        Reads single card information and assembles image

        Args:
            card_data: Card information dictionary

        Returns:
            Card image
        '''

        # Read mana cost
        mana_cost = self.write_mana_cost(card_data['manaCost'])

        # Determine card color
        card_color = mana_cost[0]

        # Intiate card image
        card_face_path = self.face_path_stem + card_color + ".png"

        card_image = self.read_nalpha_image(card_face_path)

        # Generate mana cost image
        mana_cost_image = mana_cost[1]

        # Calculate mana cost image coordinates
        mc_xcoord = self.mc_xoffset - np.shape(mana_cost_image)[1]
        mc_ycoord = self.mc_yoffset

        # Overlay mana cost image
        card_image = self.overlay_sprite(card_image, mana_cost_image, mc_xcoord, mc_ycoord)

        # Generate card name image
        card_name = card_data['name']
        name_image = self.generate_string_image(card_name, "Name")

        # Calculate name image coordinates
        name_xcoord = self.name_xoffset
        name_ycoord = self.name_yoffset

        # Overlay name image
        card_image = self.overlay_sprite(card_image, name_image, name_xcoord, name_ycoord)

        # Generate card type image
        card_type = card_data['type']

        # Legendary spell
        if card_data['legendary']:
            card_type = "Legendary " + card_type

        # Summon spell
        if card_type == "Creature":

            # Generate creature stats image
            creature_stats = card_data['creature']['power'] + "/" + card_data['creature']['toughness']
            creature_stats_image = self.generate_string_image(creature_stats, "Stats")

            # Calculate stats image coordinates
            stats_xcoord = self.stats_xoffset - np.shape(creature_stats_image)[1]
            stats_ycoord = self.stats_yoffset

            # Overlay creature stats image
            card_image = self.overlay_sprite(card_image, creature_stats_image, stats_xcoord, stats_ycoord)

            # Creature type string
            card_type = card_type + " - " + card_data['creature']['type']

        # Generate creature type image
        type_image = self.generate_string_image(card_type, "Type")

        # Calculate type image coordinates
        type_xcoord = self.type_xoffset
        type_ycoord = self.type_yoffset

        # Overlay type image
        card_image = self.overlay_sprite(card_image, type_image, type_xcoord, type_ycoord)

        # Generate rarity image
        rarity_image_path = self.font_path_stem + "Stats\\Symbols\\" + card_data['rarity'] + ".png"
        rarity_image = self.read_nalpha_image(rarity_image_path)

        # Calculate rarity image coordinates
        rarity_xcoord = self.rarity_xoffset
        rarity_ycoord = self.rarity_yoffset

        # Overlay rarity image
        card_image = self.overlay_sprite(card_image, rarity_image, rarity_xcoord, rarity_ycoord)

        # Generate illustrator image
        illustrator = "Illus. " + card_data['illustrator']
        illus_image = self.generate_string_image(illustrator, "Type")

        # Calculate illustrator image coordinates
        illus_xcoord = self.illus_xoffset - int(np.floor(np.shape(illus_image)[1]/2))
        illus_ycoord = self.illus_yoffset

        # Overlay illustrator image
        card_image = self.overlay_sprite(card_image, illus_image, illus_xcoord, illus_ycoord)

        # Overlay portrait
        portrait_path = card_data['art']
        card_portrait = self.read_nalpha_image(portrait_path)
        card_iamge = self.overlay_sprite(card_image, card_portrait, 49, 63)
    
        # Generate ability image
        ability = card_data['ability']
        ability_image = self.write_ability(ability, self.max_ability_width, self.max_ability_length)

        # Calculate ability image coordinates
        ability_xcoord = self.ability_xoffset
        ability_ycoord = self.ability_yoffset - int(np.floor(np.shape(ability_image)[0]/2))

        # Overlay ability image
        card_image = self.overlay_sprite(card_image, ability_image, ability_xcoord, ability_ycoord)

        return card_image
