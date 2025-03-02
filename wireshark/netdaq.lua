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
}


function netdaq_protocol.dissector(buffer, pinfo, tree)
 length = buffer:len()
 if length < 16 then return end

-- local magic = buffer(0,4):uint() -- "FELX" header
 local seq_id_uint = buffer(4,4):uint()
 local cmd_id_uint = buffer(8,4):uint()
 local pkt_len_uint = buffer(12,4):uint()

 pinfo.cols.protocol = netdaq_protocol.name
 pinfo.cols.info = string.format('seq=%u, CMD=0x%02X (%s)', seq_id_uint, cmd_id_uint, cmd_table[cmd_id_uint] )

 local subtree = tree:add(netdaq_protocol, buffer(), "netdaq Protocol Data")

 subtree:add(seq_id, seq_id_uint)
 subtree:add(cmd, cmd_id_uint):append_text(string.format(' (%s)', cmd_table[cmd_id_uint] ))
 subtree:add(pkt_len, pkt_len_uint)
 if (length > 16) then
	local payload_len = length - 16
--	print(string.format('len: %u, PL_len: %u, ', length, payload_len))
	 subtree:add(payload, buffer(16,payload_len))
	 pinfo.cols.info:append(string.format(', pl_len=%u', payload_len))
 end
end

local tcp_port = DissectorTable.get("tcp.port")
tcp_port:add(4369, netdaq_protocol)

