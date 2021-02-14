
memreads = {
    [0x3AA0] = 0x3F1F - 0x3AA0,
    [0x00B1] = 1,
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
            memory.write_u8(addr, b3)
        else
            io.close(inp)
            -- truncate file to let bot know it's done
            io.open("instr", "w"):close()
            break
        end
    end

    -- TODO: look into hash_region
    -- Read battle memory $3AA0-$3F1F
    mem = memory.readbyterange(0x3AA0, 0x3F1F - 0x3AA0)

    -- Write binary to disk
    memfile = io.open("_memfile", "wb")

    -- TODO: Perhaps have it read this from a file
    for addr,mlen in pairs(memreads) do
        --print(addr .. " " .. mlen)
        mem = memory.readbyterange(addr, mlen)

        -- Write address and length of buffer
        memfile:write(string.char(bit.rshift(addr, 8)))
        memfile:write(string.char(bit.band(addr, 0xFF)))
        bufsize = #mem
        memfile:write(string.char(bit.rshift(bufsize, 8)))
        memfile:write(string.char(bit.band(bufsize, 0xFF)))

        -- Write the memory values
        for _addr,val in pairs(mem) do
            --print(addr .. " " .. val)
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
   local f = io.open("cc_status", "r")
    if f ~= nil then
        io.close(f)
        i = 0
        for line in io.lines("cc_status") do
            gui.text(20, 10 * (i + 1), line)
        end
    end
end
