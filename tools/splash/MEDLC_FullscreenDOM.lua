-- Middle-earth DLC: full-screen Dawn of Man (loading screen) pictures.
-- Inlined into LoadScreen.lua by tools/build_dlc.py (front-end skin override, Art/LoadScreen.lua).
-- The stock screen draws civ.DawnOfManImage at 1024x768 in the middle of the screen. For the pictures listed
-- here (their real pixel size) the image control is stretched to cover the whole screen instead, keeping the
-- aspect ratio and cropping the overflow evenly (like StretchMode="UniformToFill"). Every other civ keeps the
-- stock 1024x768 picture.
local MEDLC_FULLSCREEN_DOM = {
	["DOM_Hobbits.dds"] = { 3840, 2160 },
	["DOM_Mordor.dds"] = { 3840, 2160 },
}
local g_MEDLC_DOMStretched = false

function MEDLC_FitDawnOfMan(image)
	local tex = image and MEDLC_FULLSCREEN_DOM[image]
	if tex then
		local screenW, screenH = UIManager:GetScreenSizeVal()
		local texW, texH = tex[1], tex[2]
		local scale = math.max(screenW / texW, screenH / texH)
		local u, v = screenW / scale, screenH / scale       -- visible part of the texture, in texture pixels
		Controls.AlphaAnim:SetSizeVal(screenW, screenH)
		Controls.Image:SetSizeVal(screenW, screenH)
		Controls.Image:SetTextureOffsetVal(math.floor((texW - u) / 2), math.floor((texH - v) / 2))
		Controls.Image:SetTextureSizeVal(u, v)
		Controls.Image:NormalizeTexture()
		g_MEDLC_DOMStretched = true
	elseif g_MEDLC_DOMStretched then
		-- back to the stock layout for the next civ
		Controls.AlphaAnim:SetSizeVal(1024, 768)
		Controls.Image:SetSizeVal(1024, 768)
		Controls.Image:SetTextureOffsetVal(0, 0)
		Controls.Image:SetTextureSizeVal(1024, 768)
		Controls.Image:NormalizeTexture()
		g_MEDLC_DOMStretched = false
	end
end
