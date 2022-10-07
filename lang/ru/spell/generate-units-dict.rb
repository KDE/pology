#!/usr/bin/ruby18

$dict = []

def concat_pairs(a, b)
	if a.is_a?(String)
		a = [a]
	end

	res = []
	a.each do |a_word|
		b.each do |b_word|
			res << a_word + b_word
		end
	end

	res
end

def add_metric(name, suffix)
	metrix_prefix = [
		'йокто', 'зепто', 'атто', 'фемто', 'пико',
		'нано', 'микро', 'милли', 'санти', 'деци',
		'дека', 'гекто', 'кило', 'мега', 'гига',
		'тера', 'пета', 'экса', 'зетта', 'йотта']

	$dict += concat_pairs(metrix_prefix, concat_pairs(name, suffix))
end

def add_metric_ab(name)
	metrix_prefix = [
		'и', 'з', 'а', 'ф', 'п',
		'н', 'мк', 'м', 'с', 'д',
		'да', 'г', 'к', 'М', 'Г',
		'Т', 'П', 'Э', 'З', 'Й']

	$dict += concat_pairs(metrix_prefix, name)
end

def add_generic(name, suffix)
	$dict += concat_pairs(name, suffix)
end

suffix_1 = ['ы', '', 'а', 'ов', 'ах']

add_generic('лат', suffix_1)
add_generic('лит', suffix_1)
add_generic('ринггит', suffix_1)
add_generic('толар', suffix_1)
add_generic('бат', suffix_1)
add_generic('ранд', suffix_1)
add_generic('вон', ['а', '', 'ы', 'ах'])
add_generic('паундал', ['ь', 'и', 'ей', 'ях'])
add_generic('кун', ['а', '', 'ы', 'ах'])

add_metric('метр', suffix_1)
add_metric('литр', suffix_1)
add_metric('ньютон', suffix_1)
add_metric('джоул', ['ь', 'я', 'ей', 'и', 'ях'])
add_metric('герц', ['ы', 'а', '', 'ах'])
add_metric('грамм', suffix_1)
add_metric('паскал', ['ь', 'я', 'ей', 'ях', 'и'])
add_metric('секунд', ['ы', '', 'а', 'ах'])
add_metric('ватт', ['', 'а', 'ах', 'ы']) # не "ваттов"
add_metric('бар', ['', 'а', 'ы', 'ах']) # не "баров"

add_metric_ab('Дж')
add_metric_ab('Н') # Newton
add_metric_ab('Гц')
add_metric_ab('м')
add_metric_ab('г')
add_metric_ab('Па')
add_metric_ab('Вт')
add_metric_ab('л')
add_metric_ab('с')
add_metric_ab('бар')

# Write the dictionary
File.open('units-generated.aspell', 'w') do |f|
	f.puts "personal_ws-1.1 ru 0 UTF-8"

	$dict.each do |s|
		f.puts s
	end
end

