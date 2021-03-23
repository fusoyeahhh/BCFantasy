
memreads = {
    -- Button configuration
    [0x1D50] = 0x1D56 - 0x1D50,
    -- SRAM mirroring / out of battle party stats / status
    [0x1600] = 0x2000 - 0x1600,
    -- In battle party and enemy stats / status
    [0x3AA0] = 0x3F1F - 0x3AA0,
    -- Can't run flags
    [0x00B1] = 1,
    -- battle relic effects
    [0x11D5] = 5,
    -- field relic effects (moogle charm, sprint shoes)
    [0x11DF] = 1,
    -- ForceField nulled elements
    [0x3EC8] = 1,
    -- $2686-$2B85 Battle Inventory (256 + 8 items, 5 bytes each)
    [0x2686] = 0x2B85 - 0x2686,
}

-- Main loop
while true do
	emu.frameadvance()

    -- TODO: Perhaps have the memory dumped on request
    -- Read instructions
    inp = io.open("instr", "rb")
    while inp ~= nil do
        byte = inp:read(3)
        --local data = inp:read("*all")
        --local b1,b2,b3,b4,b5 = string.byte(data,1,5)
        if byte ~= nil then
            b1, b2, b3 = string.byte(byte, 1, 3)
            -- 2 byte location
            addr = b1 * 0x100 + b2
            -- 1 byte write value
            print("Writing " .. b3 .. " to address " .. addr)
            mainmemory.write_u8(addr, b3)
        else
            io.close(inp)
            -- truncate file to let bot know it's done
            io.open("instr", "w"):close()
            break
        end
    end

    -- TODO: look into hash_region
    -- Read battle memory $3AA0-$3F1F
    mem = mainmemory.readbyterange(0x3AA0, 0x3F1F - 0x3AA0)

    -- Write binary to disk
    memfile = io.open("_memfile", "wb")

    -- FIXME: temporary work around to check battle state
    in_battle = mainmemory.read_u8(0x3A76) > 0 and --memory.read_u8(0x3A77) > 0 and
        mainmemory.read_u8(0x3A76) <= 4 --and memory.read_u8(0x3A77) <= 6
    memfile:write(string.char(0))
    memfile:write(string.char(0))
    memfile:write(string.char(0))
    memfile:write(string.char(0))
    memfile:write(string.char(in_battle and 1 or 0))

    -- TODO: Perhaps have it read this from a file
    for addr,mlen in pairs(memreads) do
        mem = mainmemory.readbyterange(addr, mlen)

        -- Write address and length of buffer
        memfile:write(string.char(bit.rshift(addr, 8)))
        memfile:write(string.char(bit.band(addr, 0xFF)))
        -- This always returns a value which is one smaller than reality
        -- Lua... what... is wrong with you?
        bufsize = #mem
        --print(bizstring.hex(addr) .. " " .. mlen .. " " .. bufsize)
        memfile:write(string.char(bit.rshift(bufsize, 8)))
        memfile:write(string.char(bit.band(bufsize, 0xFF)))

        -- Write the memory values
        for _addr,val in pairs(mem) do
            --print(_addr .. " " .. val .. " " .. (addr + _addr) .. " " .. memory.readbyte(addr + _addr))
            memfile:write(string.char(val))
        end
    end

    io.flush(memfile)
    io.close(memfile)

    -- rename to the filename expected by python
    -- Note that because we can't find an atomic file rename
    -- that the python code is stuck waiting for polling from
    -- the lua doing this since it can catch it in between writes
    -- PLEASE NOTE HOW STUPID THIS IS. LUA: YOU ARE THE WORST.
    os.remove("memfile")
    os.rename("_memfile", "memfile")

    -- Write current events to screen
    local f = io.open("cc_status.txt", "r")
    print(f)
    if f ~= nil then
        io.close(f)
        i = 0
        for line in io.lines("cc_status") do
            gui.text(20, 10 * (i + 1), line)
            i = i + 1
        end
    end
end
