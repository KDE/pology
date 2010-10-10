#!/usr/bin/ruby

File.open('menu-names.rules', 'w') do |f|
#	f.puts "addFilterHook name=\"remove/remove-accel-msg\" on=\"msg\""

	[
		# very common menus
		['file',	'&Файл'],
		['edit',	'&Правка'],
		['view',	'&Вид'],
		['tools',	'С&ервис'],
		['settings',	'&Настройка'],
		['window',	'&Окно'],
		['help',	'&Справка'],

		# less common menus
		['zoom',	'&Масштаб'],
		['zoom_menu',	'&Масштаб'],
		['game',	'&Игра'],
		['bookmarks',	'&Закладки'],
		['project',	'П&роект'],
		['go',		'Пере&йти'],
		['image',	'&Изображение'],
		['export',	'&Экспорт'],
		['format',	'Фо&рмат'],
		['insert',	'Вст&авка'],
		['session',	'С&еанс'],

	].each do |pair|
#		f.puts "*auto_comment/ectx: Menu \\(#{pair[0]}\\)/i"
#		f.puts "valid !msgid=\"" + ([''] + pair[0].split('')).join("&?") + "\""
#		f.puts "valid msgstr=\"\(#{pair[1]}|#{pair[1].tr('&', '')}\)\""

		f.puts "{^#{ ([''] + pair[0].split('')).join("&?") }$}i"
		f.puts "valid !comment=\"ectx: Menu\""
		f.puts "valid msgstr=\"^(#{ pair[1]}|#{pair[1].tr('&', '') })$\""

		f.puts "hint=\"Перевод названия меню не соответствует стандартному переводу\""
		f.puts
	end
end

