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
magic = ProtoField.bytes("netdaq.magic" , "magic" )
seq_id = ProtoField.uint32("netdaq.seq_id" , "seq_id" )
cmd = ProtoField.uint32("netdaq.cmd" , "cmd" , base.HEX)
pkt_len = ProtoField.uint32("netdaq.pkt_len" , "pkt_len" , base.DEC)
payload = ProtoField.bytes("netdaq.payload", "payload")
delay_start = ProtoField.bytes("netdaq.delay_start", "delay_start")
interval = ProtoField.bytes("netdaq.interval", "interval")

netdaq_protocol.fields = { magic, seq_id, cmd, pkt_len, payload, delay_start, interval }


dis_error = function (e, pinfo, subtree)
	local err_code = e(0,4):uint()
	pinfo.cols.info:append(string.format(', ERROR:0x%X', err_code))
end


-- parse 2492-byte config block of SET/GET_CONFIG
dis_cfg = function (cfg, pinfo, subtree)
local flags = cfg(0,4):uint()

	parse_interval(cfg(4,16), subtree, 'interval: ')
end


-- parse Start request packet
dis_start = function (request, pinfo, subtree)
	delayed=request(0,4):uint()
	if (delayed == 1) then
		pinfo.cols.info:append(" DELAYED START @")
		subtree:add(delay_start, request(4,-1))
		parse_timedelay(request(4,-1), pinfo, subtree)
	elseif (delayed == 0) then
--		pinfo.cols.info:append(' START', seqno)
	else
		pinfo.cols.info:append(' UNKNOWN TYPE')
	end
end

-- GET/SET_TIME
dis_timedate = function (request, pinfo, subtree)
	pinfo.cols.info:append(string.format(", TIME="))
	subtree:add(delay_start, request(4,-1))
	parse_timedelay(request, pinfo, subtree)
end


cmd_table = {
	[0x00000000] = {name="PING"},
	[0x00000001] = {name="CLOSE"},
	[0x00000002] = {name="STATUS_QUERY"},
	[0x00000003] = {name="RESET"},
	[0x00000004] = {name="IERROR"},
	[0x00000064] = {name="GET_READINGS"},
	[0x00000065] = {name="GET_LASTREADING"},
	[0x00000066] = {name="SCANS_TRIGGER"},
	[0x00000067] = {name="START", handler=dis_start, expected_pl=16},
	[0x00000068] = {name="STOP"},
	[0x00000069] = {name="GET_TIME", handler=dis_timedate, expected_pl=12},
	[0x0000006A] = {name="SET_TIME", handler=dis_timedate, expected_pl=12},
	[0x0000006D] = {name="DIO_GET"},
	[0x0000006E] = {name="DIO_SET"},
	[0x0000006F] = {name="QUERY_SPY"},
	[0x00000070] = {name="GET_TOTALIZER"},
	[0x00000071] = {name="RESET_TOTALIZER"},
	[0x00000072] = {name="GET_VERSION_INFO"},
	[0x00000073] = {name="SELFTEST_BEGIN"},
	[0x00000074] = {name="SELFTEST_RESULTS"},
	[0x00000075] = {name="SET_MONITOR_CHANNEL"},
	[0x00000076] = {name="CLEAR_MONITOR_CHANNEL"},
	[0x00000077] = {name="GET_BASE_CHANNEL"},
	[0x00000078] = {name="TEMP_BLOCK"},
	[0x00000079] = {name="TEMP_LIN"},
	[0x0000007A] = {name="TEMP_REFADJ"},
	[0x0000007B] = {name="SCANS_CLEAR"},
	[0x0000007C] = {name="ENABLE_SPY"},
	[0x0000007D] = {name="DISABLE_SPY"},
	[0x0000007E] = {name="SCANS_COUNT"},
	[0x0000007F] = {name="GET_LC_VERSION"},
	[0x00000080] = {name="GET_CONFIG", handler=dis_cfg, expected_pl=2492},
	[0x00000081] = {name="SET_CONFIG", handler=dis_cfg, expected_pl=2492},
	[0xffffffff] = {name="ERROR", handler=dis_error, expected_pl=4},
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
	if (buf(0,4):uint() ~= 0x46454c58) then
		return 0
	end

	local seq_id_uint = buf(4,4):uint()
	pinfo.cols.protocol = netdaq_protocol.name
	local cmdstring = cmd_table[cmd_id_uint].name
	-- info colum : always start with seq number
	pinfo.cols.info = string.format('seq=%u', seq_id_uint)
	-- generic command header.
	pinfo.cols.info:append(string.format(', CMD=0x%02X (%s)', cmd_id_uint, cmdstring))

	local subtree = tree:add(netdaq_protocol, buf(), "netdaq Protocol Data")
	subtree:add(magic, buf(0,4))
	subtree:add(seq_id, buf(4,4))
	subtree:add(cmd, buf(8,4)):append_text(string.format(' (%s)', cmdstring ))
	subtree:add(pkt_len, buf(12,4))

	local payload_len = pkt_len_uint - 16
	local handler = cmd_table[cmd_id_uint].handler
	local expected_payload = cmd_table[cmd_id_uint].expected_pl

	-- call optional command-specific dissector
	if expected_payload and (payload_len ~= expected_payload) then
		pinfo.cols.info:append('unexpected payload length !')
		return length
	end
	if handler then
		handler(buf(16,-1), pinfo, subtree)
	end

	if ((cmdstring == "PING") and (payload_len == 4)) then
-- XXX this is not strictly correct since some queries could have different meanings for the 4-byte response
-- XXX but this would be fixed by processing packets as 'conversations' to group query+reply by sequence ID
		pinfo.cols.info:append(string.format(', STATUS:', seq_id_uint) .. buf:bytes(16,4):tohex(false, ' '))
	end

	-- handle optional payload. Two cases :
	-- 	- there is 'normal' payload data accounted for by header pkt_len field
	--	- there is 'extra' payload data, possibly another netdaq frame (unsupported right now)
	-- not sure if second case can actually happen.
	if not handler and (payload_len > 0) then
		--	print(string.format('len: %u, PL_len: %u, ', length, payload_len))
		subtree:add(payload, buf(16,payload_len))
		pinfo.cols.info:append(string.format(', pl_len=%u', payload_len))
	end
	extra_len = length - pkt_len_uint
	if (extra_len > 0) then
		pinfo.cols.info:append(string.format(', !! %u extra bytes ??', extra_len))
	end
	return length
end


-- parse start-time struct
parse_timedelay = function (td, pinfo, subtree)
	local h = td(0,1):uint()
	local m = td(1,1):uint()
	local s = td(2,1):uint()
	local mo = td(3,1):uint()
	local d = td(5,1):uint()
	local y = td(6,1):uint()
	pinfo.cols.info:append(string.format('%u:%u:%u, %u-%u-%u', h,m,s,y,m,d))
end

-- parse 'interval' field of SET/GET_CONFIG blocks
parse_interval = function (intv, subtree, headertext)
	local h = intv(0,4):uint()
	local m = intv(4,4):uint()
	local s = intv(8,4):uint()
	local ms = intv(12,4):uint()
	subtree:add(interval, intv(0,16)):set_text(headertext .. string.format('%02u:%02u:%02u.%02u', h,m,s,ms))
end



local tcp_port = DissectorTable.get("tcp.port")
tcp_port:add(4369, netdaq_protocol)

