# All entries to class_spec_abbreviations must have the first letter capitalized

class_specs_abbreviations = {
    'Death knight': {
        'Uh': 'Unholy'
        },
    'Demon hunter': {},
    'Druid': {
        'Boomie': 'Balance', 
        'Resto': 'Restoration'
        },
    'Hunter': {
        'Bm': 'Beast mastery', 
        'Mm': 'Marksman'
        },
    'Mage': {},
    'Monk': {
        'Bm': 'Brewmaster', 
        'Mw': 'Mistweaver', 
        'Ww': 'Windwalker'
        },
    'Paladin': {
        'Prot': 'Protection', 
        'Ret': 'Retribution'
        },
    'Priest': {
        'Disc': 'Discipline'
        },
    'Rogue': {
        'Assa': 'Assassination', 
        'Sub': 'Subtelty'
        },
    'Shaman': {
        'Ele': 'Elemental', 
        'Enhance': 'Enhancement', 
        'Resto': 'Restoration'
        },
    'Warlock': {
        'Affli': 'Affliction', 
        'Demo': 'Demonology', 
        'Desto': 'Destruction'
        },
    'Warrior': {
        'Prot': 'Protection'
        }
}

boost_types = ['Hourly', '1 win', 'Set rating']
bracket_boost_types = {
    '2v2': [],
    '3v3': ['Gladiator']
}


spec_emotes = {
    'Death knight': {
        'Blood': '<:blood:747166380800999555>',
        'Frost': '<:frost:747166381186875531>',
        'Unholy': '<:unholy:747166380960382997>'},
    'Demon hunter': {
        'Havoc': '<:havoc:747168010065805445>',
        'Vengeance': '<:vengance:747168010095165501>'},
    'Druid': {
        'Balance': '<:balance:747166411897569361>',
        'Feral': '<:feral:747166411977261166>',
        'Guardian': '<:guardian:747166412056821860>',
        'Restoration': '<:restoration:747166411641585716>'},
    'Hunter': {
        'Beast Mastery': '<:beastmastery:747166441438052474>',
        'Marksman': '<:marksman:747166441614082222>',
        'Survival': '<:survival:747166441685647413>'},
    'Mage': {
        'Arcane': '<:arcane:747166651530608792>',
        'Fire': '<:fire:747166651832598528>',
        'Frost': '<:frost:747166651895775273>'},
    'Monk': {
        'Brewmaster': '<:brewmaster:747166669951991959>',
        'Mistweaver': '<:mistweaver:747166671504015370>',
        'Windwalker': '<:windwalker:747166670044528701>'},
    'Paladin': {
        'Holy': '<:holy:747166688646004768>',
        'Protection': '<:protection:747166689136738334>',
        'Retribution': '<:retribution:747166689073823824>'},
    'Priest': {
        'Discipline': '<:discipline:747166708862812360>',
        'Holy': '<:holy:747166708862812250>',
        'Shadow': '<:shadow:747166708908949644>'},
    'Rogue': {
        'Assassination': '<:assassination:747166729100066957>',
        'Outlaw': '<:outlaw:747189516804030675>',
        'Subtelty': '<:subtlety:747166729351856248>'},
    'Shaman': {
        'Elemental': '<:elemental:747166745537675406>',
        'Enhancement': '<:enhancement:747166745504251985>',
        'Restoration': '<:restoration:747166745818693643>'},
    'Warlock': {
        'Affliction': '<:affliction:747166770439258162>',
        'Demonology': '<:demonology:747166770292326551>',
        'Destruction': '<:destruction:747166769898061885>'},
    'Warrior': {
        'Arms': '<:arms:747166787363405865>',
        'Fury': '<:fury:747166787459743907>',
        'Protection': '<:protection:747166787120136214>'}
}

class_emotes = [
                '<:deathknight:744985782959341679>Death Knight',
                '<:demonhunter:744985799430373376>Demon Hunter',
                '<:druid:744985809538646089>Druid',
                '<:hunter:744985819303116802>Hunter',
                '<:mage:744985829633425618>Mage',
                '<:monk:744985837489618945>Monk',
                '<:paladin:744985850995278014>Paladin',
                '<:priest:744985863791968445>Priest',
                '<:rogue:744985881588531390>Rogue',
                '<:shaman:744985900865421505>Shaman',
                '<:warlock:744985911133208588>Warlock',
                '<:warrior:744985921098874920>Warrior'
                ]

connected_realms = [
    ['Antonidas'],
    ['Archimonde'],
    ['Argentdawn'],
    ['Blackhand', "Mal'ganis"],
    ['Blackmoore'],
    ['Blackrock'],
    ['Burninglegion', "Al'akir", 'Skullcrusher', 'Xavius'],
    ['Dalaran', "Cho'gall", "Eldre'thalas", 'Marécagedezangar', 'Sinstralis'],
    ['Deathwing', 'Karazhan', "Lightning's Blade", 'The Maelstrom'],
    ['Defiasbrotherhood', 'Ravenholdt', 'Scarshield legion', 'Sporeggar', 'The venture co'],
    ['Doomhammer', 'Turalyon'],
    ['Draenor'],
    ['Dragonmaw', 'Haomarush', 'Spinebreaker', 'Vashj'],
    ["Drak'thul", 'Burningblade'],
    ['Elune'],
    ['Eredar'],
    ['Frostmane', 'Grimbatol', 'Aggra'],
    ['Frostwolf'],
    ['Hyjal'],
    ['Kazzak'],
    ['Khazmodan'],
    ['Magtheridon'],
    ['Malfurion', 'Malygos'],
    ['Nemesis'],
    ['Onyxia', 'Dethecus', "Mug'thol", 'Terrordar', 'Theradras'],
    ['Outland'],
    ['Ragnaros'],
    ['Ravencrest'],
    ['Runetotem', 'Nagrand', 'Arathor', 'Hellfire', 'Kilrogg'],
    ['Sargeras', 'Garona', "Ner'zhul"],
    ['Silvermoon'],
    ['Stormreaver'],
    ['Stormscale'],
    ['Sylvanas', 'Auchindoun', 'Dunemaul', 'Jaedenar'],
    ['Tarrenmill', 'Dentarg'],
    ['Thrall'],
    ['Turalyon', 'Doomhammer'],
    ['Twistingnether'],
    ["Vol'jin", 'Chantséternels'],
    ['Ysondre']
]

realm_abbreviations = {
    "Tn": "Twistingnether",
    "Tm": "Tarrenmill",
    "Voljin": "Vol'jin",
    "Vol Jin": "Vol'jin",
    "Chantseternels": "Chantséternels"
}

# when displaying any string from bank_characters, format using horde and alliance emotes in config.json
bank_characters = {
    "Kazzak": "{0}Pakix-Kazzak",
    "Twistingnether": "{0}Pakix-TwistingNether",
    "Tarrenmill": "{0}Pakix-TarrenMill",
    "Draenor": "{0}Pakix-Draenor",
    "Ragnaros": "{0}Pakix-Ragnaros",
    "Stormscale": "{0}Pakixx-Stormscale",
    "Drak'thul": "{0}Pakix-Drak'thul",
    "Burninglegion": "{0}Pakix-BurningLegion",
    "Magtheridon": "{0}Pakix-Magtheridon",
    "Deathwing": "{0}Pakix-Deathwing",
    "Stormreaver": "{0}Pakix-Stormreaver",
    "Blackhand": "{0}Pakix-Blackhand",
    "Blackmoore": "{0}Pakix-Blackmoore or {1}AllyHaki-Blackmoore",
    "Blackrock": "{0}Pakix-Blackrock",
    "Eredar": "{0}Pakix-Eredar",
    "Thrall": "{0}Pakixx-Thrall",
    "Hyjal": "{0}Pakixx-Hyjal or {1}Allyhaki-Hyjal",
    "Ysondre": "{0}Pakix-Ysondre or {1}Allyhaki-Ysondre",
    "Archimonde": "{0}Pakix-Archimonde or {1}Allyhaki-Archimonde",
    "Dalaran": "{0}Pakix-Dalaran or {1}AllyHaki-Dalaran",
    "Khazmodan": "{0}Pakix-KhazModan",
    "Sargeras": "{0}Pakix-Sargeras",
    "Elune": "{0}Pakix-Elune or {1}Allyhaki-Elune",
    "Nemesis": "{0}Pakix-Nemesis",
    "Ravencrest": "{0}HordeHaki-Ravencrest or {1}AllyHaki-Ravencrest",
    "Silvermoon": "{0}HordeHaki-Silvermoon or {1}AllyHaki-Silvermoon",
    "Outland": "{0}HordeHaki-Outland or {1}AllyHaki-Outland",
    "Argentdawn": "{0}HordeHaki-ArgentDawn or {1}AllyHaki-ArgentDawn",
    "Sylvanas": "{0}HordeHaki-Sylvanas or {1}AllyHaki-Sylvanas",
    "Frostmane": "{0}Hordehaki-Frostmane or {1}Allyhaki-Frostmane",
    "Malfurion": "{0}Hordehaki-Malfurion or {1}Allyhaki-Malfurion",
    "Runetotem": "{0}Hordehaki-Runetotem or {1}Allyhaki-Runetotem",
    "Doomhammer": "{0}Hordehaki-Doomhammer",
    "Defiasbrotherhood": "{0}HordeHaki-DefiasBrotherhood or {1}Allyhaki-DefiasBrotherhood",
    "Frostwolf": "{0}HordeHaki-Frostwolf",
    "Onyxia": "{0}HordeHaki-Onyxia",
    "Vol'jin": "{0}Hordehaki-Vol'jin",
    "Turalyon": "{1}Allyhaki-Turalyon",
    "Antonidas": "{1}Allyhaki-Antonidas",
}
