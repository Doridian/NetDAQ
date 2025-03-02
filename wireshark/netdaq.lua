-- Fluke NetDAQ dissector for wireshark
-- (c) fenugrec 2025
--
-- place or symlink in $HOME/.local/lib/wireshark/plugins
-- to reload : Analyze->reload LUA plugins

-- limitations :
-- -hardcoded port
-- some hardcoded command numbers  due to lua ignorance

netdaq_protocol = Proto("netdaq", "Fluke NetDAQ protocol")

-- all fields must be 'registered' even if they may be missing e.g. payload
seq_id = ProtoField.uint32("netdaq.seq_id" , "seq_id" )
cmd = ProtoField.uint32("netdaq.cmd" , "cmd" , base.HEX)
pkt_len = ProtoField.uint32("netdaq.pkt_len" , "pkt_len" , base.DEC)
payload = ProtoField.bytes("netdaq.payload", "payload")

netdaq_protocol.fields = { message_length, seq_id, cmd, pkt_len, payload}


cmd_table = {
	[0x00000000] = "PING",
	[0x00000001] = "CLOSE",
	[0x00000002] = "STATUS_QUERY",
	[0x00000064] = "GET_READINGS",
	[0x00000067] = "START",
	[0x00000068] = "STOP",
	[0x0000006A] = "SET_TIME",
	[0x0000006F] = "QUERY_SPY",
	[0x00000071] = "RESET_TOTALIZER",
	[0x00000072] = "GET_VERSION_INFO",
	[0x00000075] = "SET_MONITOR_CHANNEL",
	[0x00000076] = "CLEAR_MONITOR_CHANNEL",
	[0x00000077] = "GET_BASE_CHANNEL",
	[0x0000007C] = "ENABLE_SPY",
	[0x0000007D] = "DISABLE_SPY",
	[0x0000007F] = "GET_LC_VERSION",
	[0x00000081] = "SET_CONFIG",
	[0xffffffff] = "ERROR",
}


-- based on "fpm.lua" example from wireshark wiki, but with a (bold) assumption that there will not be
-- multiple netdaq packets in a same TCP frame.
function netdaq_protocol.dissector(buf, pinfo, tree)
	tvbs = {}

	local pktlen = buf:len()

	local result = dis(buf, pinfo, tree)
	if result > 0 then
		return result
	elseif result == 0 then
		-- some error, pass up
		return 0
	else
		-- need more
		pinfo.desegment_len = DESEGMENT_ONE_MORE_SEGMENT
	end

	-- pinfo.desegment_offset = length
end


-- local function to dissect reassembled netdaq packet.
-- return (-missing) if we need more data
-- return (len) if succesfully parsed
-- return 0 if error
dis = function (buf, pinfo, tree)
	length = buf:len()
	if length < 16 then return 0 end

	local cmd_id_uint = buf(8,4):uint()
	local pkt_len_uint = buf(12,4):uint()

	if (length < pkt_len_uint) then
	     return (length - pkt_len_uint)
	end

	-- validate "FELX" marker
	local magic = buf(0,4):uint()
	if (magic ~= 0x46454c58) then
		return 0
	end

	local seq_id_uint = buf(4,4):uint()
	pinfo.cols.protocol = netdaq_protocol.name
	pinfo.cols.info = string.format('seq=%u, CMD=0x%02X (%s)', seq_id_uint, cmd_id_uint, cmd_table[cmd_id_uint] )

	local subtree = tree:add(netdaq_protocol, buf(), "netdaq Protocol Data")

	subtree:add(seq_id, seq_id_uint)
	subtree:add(cmd, cmd_id_uint):append_text(string.format(' (%s)', cmd_table[cmd_id_uint] ))
	subtree:add(pkt_len, pkt_len_uint)

	-- handle a few special messages

	if ((cmd_table[cmd_id_uint] == "ERROR") and (length == 20)) then
		local err_code = buf(16,4):uint()
		pinfo.cols.info = string.format('seq=%u, ERROR:0x%X', seq_id_uint, err_code)
	end

	if ((cmd_table[cmd_id_uint] == "PING") and (length == 20)) then
-- XXX this is not strictly correct since some queries could have different meanings for the 4-byte response
-- XXX but this would be fixed by processing packets as 'conversations' to group query+reply by sequence ID
		pinfo.cols.info = string.format('seq=%u, STATUS:', seq_id_uint) .. buf:bytes(16,4):tohex(false, ' ')
	end


	-- handle optional payload

	if (length > 16) then
		local payload_len = length - 16
		--	print(string.format('len: %u, PL_len: %u, ', length, payload_len))
		subtree:add(payload, buf(16,payload_len))
		pinfo.cols.info:append(string.format(', pl_len=%u', payload_len))
	end
	return length
end

local tcp_port = DissectorTable.get("tcp.port")
tcp_port:add(4369, netdaq_protocol)

