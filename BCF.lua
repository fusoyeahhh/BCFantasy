kills = {}
wound = {false, false, false, false}
cparty = {nil, nil, nil, nil}
ekilled = {}
pdeath = {}
-- in_battle requires the number of enemies and characters alive to be greater
-- than zero, and less than their allowed slot numbers (6 and 4 respectively).
-- It's probably not perfect, but seems to work so far
in_battle = mainmemory.read_u8(0x3A76) > 0 and mainmemory.read_u8(0x3A77) > 0
 	    and mainmemory.read_u8(0x3A76) <= 4 and mainmemory.read_u8(0x3A77) <= 6
enemies_alive = 0
map_id = nil

-- character slot order
_CHARS = {
	"TERRA",
	"LOCKE",
	"CYAN",
	"SHADOW",
	"EDGAR",
	"SABIN",
	"CELES",
	"STRAGO",
	"RELM",
	"SETZER",
	"MOG",
	"GAU",
	"GOGO",
	"UMARO",
	"EXTRA1",
	"EXTRA2"
}

offset_lower = 169 - 112

-- At some point it would be nice to get this working
--ip = comm.socketServerGetIp()
--port = comm.socketServerGetPort()
ip = nil
port = nil

-- Read seed and flag information
--[[
    replace_credits_text(0x6625, "flags")
    replace_credits_text(0x663A, display_flags, split=True)
    replace_credits_text(0x6661, codestatus)
    replace_credits_text(0x6682, "seed")
    replace_credits_text(0x668C, text.upper())
    replace_credits_text(0x669E, "ver.")

-- FIXME: These are locations *in the ROM* not in memory
-- and they're compressed too...
flags = ""
for i=0x663A..0x6661 do
	flags = flags .. memory.read_u8(i) .. "|"
end

seed = ""
for i=0x668C..0x669E do
	seed = seed .. memory.read_u8(i) .. "|"
end
--]]

-- Truncate any existing logfile
logfile = io.open("logfile.txt", "w+")
io.close(logfile)

-- FIXME: remove this eventually
_HUD = true

-- Main loop
while true do

	-- FIXME: do variable state comparison here
	emu.frameadvance()

	prev_state = in_battle
	in_battle = mainmemory.read_u8(0x3A76) > 0 and --mainmemory.read_u8(0x3A77) > 0 and
			mainmemory.read_u8(0x3A76) <= 4 --and mainmemory.read_u8(0x3A77) <= 6
	if prev_state ~= in_battle and in_battle then
		enemies_alive = mainmemory.read_u8(0x3A77)
		ekilled = {}
		-- FIXME: Initialize this properly
		wound = {}
		cparty = {nil, nil, nil, nil}
	end

	map_change = bit.band(mainmemory.read_u16_le(0x1F64), 0x200 - 1)
	map_change = map_change ~= map_id
	map_id = bit.band(mainmemory.read_u16_le(0x1F64), 0x200 - 1)
	area_id = mainmemory.read_u8(0x0520)
	miab_id = mainmemory.read_u16_le(0x00D0)
	eform_id = mainmemory.read_u16_le(0x11E0)
	battle_type = mainmemory.read_u8(0x3EBC)
	final_kefka = mainmemory.read_u8(0x9A) and in_battle and eform_id == 511

	music_change = music_id
	-- Music id detection, from Myriachan
	-- "if 0x1304 is 0x10, 0x11, 0x14, or 0x15, then 0x1305 should contain a song ID."
	mbit = mainmemory.read_u8(0x1304)
	if mbit == 0x10 or mbit == 0x11 or mbit == 0x14 or mbit == 0x15 then
		music_id = mainmemory.read_u8(0x1305)
		music_change = music_change ~= music_id
	else
		music_id = -1
	end

	-- Game over detection
	-- Another from Myria: "another way to identify game over is reading the 24-bit value at 0x00E5.
	-- 0xCCE5C5 is one of the event script pointers for the game over script."
	is_gameover = bit.band(mainmemory.read_u32_le(0x00E5), 0xFFFFFF) == 0xCCE5C5

	-- MIAB detection, thanks to Myriachan
	is_miab = miab_id == 0x0B90
	-- clear miab flag
	-- FIXME: Reenable after debug
	--if is_miab then
		--mainmemory.write_u16_le(0x00D0, 0)
	--end

	-- Another from Myriachan
	is_veldt = bit.band(mainmemory.read_u8(0x11F9), 0x40) == 0x40
	is_veldt = is_veldt and (map_id == 0)

	-- need to learn offsets relative to ASCII
	--[[
	name_1 = string.char(math.max(memory.read_u8(0x2EAF) - offset_lower, 0))
	name_2 = string.char(math.max(memory.read_u8(0x2EB0) - offset_lower, 0))
	name_3 = string.char(math.max(memory.read_u8(0x2EB1) - offset_lower, 0))
	name_4 = string.char(math.max(memory.read_u8(0x2EB2) - offset_lower, 0))
	name_5 = string.char(math.max(memory.read_u8(0x2EB3) - offset_lower, 0))
	name_6 = string.char(math.max(memory.read_u8(0x2EB4) - offset_lower, 0))
	--]]

	-- next two work
	nchar_alive = mainmemory.read_u8(0x3A76)
	nenem_alive = mainmemory.read_u8(0x3A77)

	-- appears to work, but only for party, not enemies
	alive_mask = mainmemory.read_u8(0x3A74)

	if _HUD then
		gui.text(20, 10, "in battle? " .. tostring(in_battle) .. " | eform id " .. eform_id .. " | is gameover " .. tostring(is_gameover) .. "(" .. tostring(is_miab) .. ")" .. " | map id " .. map_id .. " | music id " .. music_id)
		gui.text(20, 20, "alive mask: " .. bizstring.binary((0xF + 1) + alive_mask) .. " total enemies " .. enemies_alive .. " final kefka " .. tostring(final_kefka))
		gui.text(20, 30, "chars alive: " .. nchar_alive)
		gui.text(20, 40, "monsters alive: " .. nenem_alive)
	end

	-- $EBFF-$EC06 monster names (4 items, 2 bytes each)
	-- must be pointers
	e1_name = string.char(math.max(mainmemory.read_u8(0xEBFF) - offset_lower, 0)) ..
		  string.char(math.max(mainmemory.read_u8(0xEC00) - offset_lower, 0))

    	-- $EC07-$EC0E number of monsters alive for each name (4 items, 2 bytes each)
	e1_count = mainmemory.read_u8(0xEC07)
	--gui.text(20, 70, "enemy slot 1: " .. e1_name .. " (" .. e1_count  .. ")")

	-- map slot to actor
	chars = {[0xFF] = "ERROR"}
	for i,char in ipairs(_CHARS) do
		cslot = mainmemory.read_u8(0x3000 + i - 1)
		-- Strange mapping here
		if cslot < 0xF then
			chars[cslot] = char
		elseif cslot ~= 0xFF then
			chars[cslot] = "ERROR slot reported -> " .. cslot
		end
	end

	-- Crowd control potential
	--[[
	s = 5
	d = 6
	for j=0,3 do
		memory.write_u8(0x1602 + 0x25 * d + j, memory.read_u8(0x1602 + 0x25 * s + j))
	end
	j = 4
	-- increment character in certain position
	memory.write_u8(0x1602 + 0x25 * d + j, memory.read_u8(0x1602 + 0x25 * s + j) + 1)

	-- write char names to screen
	for i,char in ipairs(_CHARS) do
		cname = ""
		for j=0,5 do
			cname = cname .. string.char(math.max(memory.read_u8(0x1602 + 0x25 * (i - 1) + j) - offset_lower, 0))
		end
		
		gui.text(20, 360 + i * 10, i .. " " .. cname)
	end
	--]]

	-- TODO: short circuit all of this outside of battle
	-- targetting 0x3290 - 0x3297 slots 1-4 (indicates "masks")
	for i=0,3 do
		c_last_targetted = mainmemory.read_u8(0x3290 + i)
		curr_hp = mainmemory.read_u16_le(0x3BF4 + 2 * i)
		slot_mask = mainmemory.read_u16_le(0x3018 + 2 * i)
		char_status_1 = mainmemory.read_u16_le(0x2E98 + 2 * i)

		char = "EMPTY?"
		if chars[2 * i] ~= nil then
			char = chars[2 * i]
			cparty[i + 1] = char
		end
		slot_mask = bizstring.hex(mainmemory.read_u16_le(0x3018 + 2 * i))

		_wound = bit.band(char_status_1, bit.lshift(1, 7)) == 128
		_petrify = bit.band(char_status_1, bit.lshift(1, 6)) == 64
		_zombie = bit.band(char_status_1, bit.lshift(1, 1)) == 2
		_wound = _wound or _petrify or _zombie
		-- Check if
		-- 1. We're in battle and we didn't *just* get here
		-- If we did, then only record the wound status (e.g. we were dead coming in)
		-- 2. The wound status got toggled
		-- 3. How many enemies are there? It's possible that the game starts overwriting battle memory before
		-- we can catch the transition for in_battle. This attempts to catch if there aren't any enemies alive
		-- and takes no action if there isn't
		if in_battle and (prev_state == in_battle) and nenem_alive > 0 and (_wound and (not wound[i])) and char ~= "EMPTY?" then
		    if pdeath[char] ~= nil then
    		    pdeath[char] = pdeath[char] + 1
    		else
        		pdeath[char] = 1
		    end
		end
		wound[i] = _wound

		if _HUD then
			gui.text(20, 60 + i * 10, char .. " (" .. (2 * i ) .. ") | slot " .. slot_mask .. " | " .. curr_hp
					.. " | targetted by: " .. bizstring.hex(c_last_targetted) .. " | status: "
					.. bizstring.binary(char_status_1) .. " | wound: " .. tostring(_wound))
		end
	end

	-- 0x3298 monster slots 1-6? (indicates "masks")
	for i=0,5 do
		curr_hp = mainmemory.read_u16_le(0x3BF4 + 8 + 2 * i)
		_slot_mask = mainmemory.read_u16_le(0x3020 + 2 * i)
		slot_mask = bizstring.hex(mainmemory.read_u16_le(0x3020 + 2 * i))
		status = ""

		-- status reads
		sbyte_1 = mainmemory.read_u8(0x3EE4 + 8 + 2 * i)
		is_wounded = bit.band(sbyte_1, 0x80)
		is_petrified = bit.band(sbyte_1, 0x40)
		is_zombied = bit.band(sbyte_1, 0x2)
		sbyte_1 = bizstring.binary(sbyte_1)

		-- Determine who killed this monster
		-- We must:
		-- 	* be in battle
		-- 	* not be an invalid (read nil) slot
		-- 	* not have an invalid (read nil) character targetting us
		-- 	* have curr_hp == 0 (this may not be sufficient)
		-- 	* have less enemies alive than last time we checked
		c_last_targetted = mainmemory.read_u8(0x3298 + 2 * i)
		status = " killed by "
		if in_battle and _slot_mask ~= 255 and c_last_targetted ~= 255
				and (curr_hp == 0 or is_wounded or is_zombied or is_petrified)
				and nenem_alive < enemies_alive then
			status = status .. c_last_targetted

			-- Attribute kill to the last character that targetted this
			if c_last_targetted ~= nil then
				c_last_targetted = chars[c_last_targetted]
				-- How we get to this, I don't know...
				if c_last_targetted == nil then
					c_last_targetted = 'NIL_lookup'
				end
			else
				-- Attempt to handle error
				c_last_targetted = "ERROR"
			end

			if ekilled[slot_mask] == nil then
				-- Initialize and/or increment
				if kills[c_last_targetted] == nil then
					kills[c_last_targetted] = 1
				else
					kills[c_last_targetted] = kills[c_last_targetted] + 1
				end
				-- Decrement running enemy count
				enemies_alive = enemies_alive - 1
				-- Mark as dead
				ekilled[slot_mask] = 1
			end
			--else
			--status = bizstring.hex(c_last_targetted)
		end

		if _HUD then
			gui.text(20, 120 + i * 10, "slot " .. slot_mask
					.. " status byte: " .. sbyte_1
					.. " (" .. curr_hp .. ") targetted by: "
					.. c_last_targetted
					.. status)
		end
	end

	-- Display kill tracker
	i = 0
	for char,kcount in pairs(kills) do
	    if pdeath[char] ~= nil then
	        kcount = kcount .. " deaths: " .. pdeath[char]
	    end

		if _HUD then
			gui.text(20, 240 + i * 10, "slot " .. char .. " kills: " .. kcount)
		end
		i = i + 1
    end

    --[[
	i = 0
	for e,kcount in pairs(ekilled) do
		gui.text(20, 360 + i * 10, e .. " DED")
		i = i + 1
    end
    --]]

	frame_counter = emu.framecount()
	out_json = "{"
	-- General information
	out_json = out_json .. "\"frame\": " .. frame_counter .. ","
	out_json = out_json .. "\"miab_id\": " .. miab_id .. ","
	out_json = out_json .. "\"area_id\": " .. area_id .. ","
	out_json = out_json .. "\"eform_id\": " .. eform_id .. ","
	out_json = out_json .. "\"in_battle\":" .. tostring(in_battle) .. ","
	out_json = out_json .. "\"is_miab\":" .. tostring(is_miab) .. ","
	out_json = out_json .. "\"is_veldt\":" .. tostring(is_veldt) .. ","
	out_json = out_json .. "\"is_gameover\":" .. tostring(is_gameover) .. ","
	out_json = out_json .. "\"map_id\": " .. map_id .. ","
	out_json = out_json .. "\"music_id\": " .. music_id .. ","

	-- secondary state check
	out_json = out_json .. "  \"state\": [" .. ""
	for i,b in pairs(mainmemory.readbyterange(0x3000, 16)) do
		out_json = out_json .. "\"" .. b .. "\""
		if i ~= 0 then
			out_json = out_json .. ", "
		end
    end
	out_json = out_json .. "]"

	-- Kill information
	out_json = out_json .. ",  \"kills\": {" .. ""
	i = 0
	for char,kcount in pairs(kills) do
		app =  ", "
		i = i + 1
		if i == #kills then
			app = ""
		end
		out_json = out_json .. "\"" .. char .. "\": " ..  kcount .. app
    end
	out_json = out_json .. "}"

	-- battle party information
	out_json = out_json .. ", \"cparty\": ["
	for i=1,4 do
		if cparty[i] ~= nil then
			out_json = out_json .. "\"" .. cparty[i] .. "\""
		else
			out_json = out_json .. "\"EMPTY\""
		end
		if i ~= 4 then
			out_json = out_json .. ", "
		end
	end
	out_json = out_json .. "]"

	-- party information
	out_json = out_json .. ", \"party\": {"
	for i=0,15 do
		actor = mainmemory.read_u8(0x1600 + i * 0x25)
		name = mainmemory.readbyterange(0x1602 + i * 0x25 - 1, 7)
		out_json = out_json .. "\"" .. actor .. "\": \""
		for j,c in ipairs(name) do
			out_json = out_json .. c .. " "
		end
		out_json = out_json .. "\""
		if i ~= 15 then
			out_json = out_json .. ", "
		end
	end
	out_json = out_json .. "}"

	-- death information
	out_json = out_json .. ", \"deaths\": {" .. ""
	i = 0
	for char,dcount in pairs(pdeath) do
		app =  ", "
		i = i + 1
		if i == #pdeath then
			app = ""
		end
		out_json = out_json .. "\"" .. char .. "\": " ..  dcount .. app
    end
	out_json = out_json .. "}"

	out_json = out_json .. "}" 

	--prev_state = in_battle
	--in_battle = mainmemory.read_u8(0x3A76) > 0 and --mainmemory.read_u8(0x3A77) > 0 and
        	    --mainmemory.read_u8(0x3A76) <= 4 --and mainmemory.read_u8(0x3A77) <= 6

	--if in_battle or map_change then
	if is_gameover or map_change or music_change or (prev_state ~= in_battle) or final_kefka
			or frame_counter % 600 == 0 then
		logfile = io.open("logfile.txt", "a")
		logfile:write(out_json .. "\n")
		io.flush(logfile)
		io.close(logfile)
	end
end
